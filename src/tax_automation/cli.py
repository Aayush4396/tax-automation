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

    args = parser.parse_args()

    if args.command == "process":
        from tax_automation.pipeline.narration import process_entity_narration

        in_p = Path(args.input) if args.input else None
        out_p = Path(args.output) if args.output else None
        process_entity_narration(args.entity, args.fy, in_p, out_p)
    elif args.command == "consolidate":
        out = consolidate_entity_statements(args.entity, args.fy)
        print(f"[OK] Statement consolidation complete: {out}")


if __name__ == "__main__":
    main()
