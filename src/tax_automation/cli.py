# -*- coding: utf-8 -*-
"""
cli.py
======
Unified command-line interface entry point for the tax_automation pipeline.

Usage:
    python -m tax_automation process --entity aayush --fy FY26
    python -m tax_automation consolidate --entity ajay --fy FY26
"""

from __future__ import annotations
import argparse
import io
import logging
from pathlib import Path
import sys

from tax_automation.consolidators.generic_consolidator import (
    consolidate_entity_statements,
)

logger = logging.getLogger("tax_automation")


def main():
    # Force UTF-8 output on Windows if applicable
    if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
        sys.stdout = io.TextIOWrapper(
            sys.stdout.buffer, encoding="utf-8", errors="replace"
        )

    parser = argparse.ArgumentParser(description="Tax Automation CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    proc_parser = subparsers.add_parser(
        "process", help="Process narration for an entity profile"
    )
    proc_parser.add_argument(
        "--entity", required=True, help="Entity profile ID (e.g. aayush, ajay, sunita)"
    )
    proc_parser.add_argument("--fy", default="FY26", help="Financial year (e.g. FY26)")
    proc_parser.add_argument("--input", default=None, help="Input Excel path")
    proc_parser.add_argument("--output", default=None, help="Output Excel path")

    conso_parser = subparsers.add_parser(
        "consolidate", help="Consolidate raw bank statements"
    )
    conso_parser.add_argument("--entity", required=True, help="Entity profile ID")
    conso_parser.add_argument("--fy", default="FY26", help="Financial year")

    init_parser = subparsers.add_parser(
        "init-entity", help="Scaffold a new taxpayer entity profile and directories"
    )
    init_parser.add_argument(
        "--entity", required=True, help="Entity ID (lowercase alphanumeric)"
    )
    init_parser.add_argument(
        "--name", required=True, help="Full legal name of taxpayer"
    )
    init_parser.add_argument("--pan", default=None, help="PAN number (optional)")
    init_parser.add_argument(
        "--fy", default="FY26", help="Target Financial Year (e.g. FY26)"
    )

    args = parser.parse_args()

    if args.command == "process":
        from tax_automation.pipeline.narration import process_entity_narration

        in_p = Path(args.input) if args.input else None
        out_p = Path(args.output) if args.output else None
        process_entity_narration(args.entity, args.fy, in_p, out_p)
    elif args.command == "consolidate":
        out = consolidate_entity_statements(args.entity, args.fy)
        print(f"[OK] Statement consolidation complete: {out}")
    elif args.command == "init-entity":
        _init_entity(args.entity, args.name, args.pan, args.fy)


def _init_entity(
    entity_id: str, display_name: str, pan: str | None, fy: str
) -> None:
    """Scaffolds configuration and directories for a new entity."""
    import json
    import re
    from tax_automation.config_loader import (
        CONFIG_DIR,
        resolve_input_dir,
        resolve_output_dir,
    )

    eid = entity_id.strip().lower()
    if not re.match(r"^[a-z0-9_]+$", eid):
        print(
            f"[ERROR] Invalid entity_id '{eid}'. "
            "Must be lowercase alphanumeric/underscore."
        )
        sys.exit(1)

    entities_dir = CONFIG_DIR / "entities"
    entities_dir.mkdir(parents=True, exist_ok=True)
    cfg_path = entities_dir / f"{eid}.json"

    if cfg_path.exists():
        print(f"[WARNING] Entity configuration already exists at {cfg_path}")
    else:
        norm_name = re.sub(r"\s+", r"\\s*", display_name.upper())
        profile_data = {
            "$schema": "../schemas/entity.json",
            "entity_id": eid,
            "display_name": display_name,
            "pan": pan or "",
            "self_patterns": [norm_name],
            "self_vpas": [],
            "family_members": [],
            "rent": {
                "landlords": [],
                "vpas": [],
                "keywords": []
            },
            "custom_rules": [],
            "output_sheet_names": [
                "For Tally",
                "Conso",
                "Bank Summary",
                "Monthly Pivot",
                "Guidelines"
            ],
            "accounts": []
        }
        with open(cfg_path, "w", encoding="utf-8") as f:
            json.dump(profile_data, f, indent=2)
        print(f"[OK] Created entity configuration: {cfg_path}")

    in_dir = resolve_input_dir(eid, fy, "bank_statements")
    out_dir = resolve_output_dir(eid, fy)
    in_dir.mkdir(parents=True, exist_ok=True)
    out_dir.mkdir(parents=True, exist_ok=True)
    print(f"[OK] Created input directory: {in_dir}")
    print(f"[OK] Created output directory: {out_dir}")
    print("\nNext steps:")
    print(f"1. Add bank accounts to {cfg_path}")
    print(f"2. Place raw statements into {in_dir}")
    print(f"3. Run: python -m tax_automation consolidate --entity {eid} --fy {fy}")
    print(f"4. Run: python -m tax_automation process --entity {eid} --fy {fy}")


if __name__ == "__main__":
    main()
