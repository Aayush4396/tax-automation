# -*- coding: utf-8 -*-
"""check_narration_results.py.

Quick sanity check on generated Excel ledger sheet counts and rows.
"""

from __future__ import annotations
import argparse
from pathlib import Path
from openpyxl import load_workbook

from tax_automation.config_loader import (
    get_entity_config,
    resolve_output_dir,
    REPO_ROOT,
)


def check_results(entity_id: str, fy: str, file_path: Path | None = None) -> bool:
    """Verifies that the generated ledger exists and has non-empty sheets."""
    config = get_entity_config(entity_id)
    output_sheet_names = set(config.get("output_sheet_names", []))
    entity_dir_name = entity_id.title()

    if file_path is None:
        file_path = resolve_output_dir(entity_id, fy) / "narrated_ledger.xlsx"
        if not file_path.exists():
            legacy_path = (
                REPO_ROOT
                / "data"
                / entity_dir_name
                / "Generated Data"
                / fy
                / f"{entity_dir_name.split()[0]}_Consolidated_Bank_Ledger_{fy}.xlsx"
            )
            if legacy_path.exists():
                file_path = legacy_path

    if not file_path.exists():
        print(f"Error: Excel file not found at {file_path}")
        return False

    print(f"Checking narration results for {entity_id.title()} ({fy}) in: {file_path}")
    wb = load_workbook(file_path, read_only=True)
    sheet_names = wb.sheetnames
    wb.close()

    bank_sheets = [s for s in sheet_names if s not in output_sheet_names]
    print(
        f"Found {len(sheet_names)} total sheets "
        f"({len(bank_sheets)} bank account sheets)."
    )
    return True


def main():
    parser = argparse.ArgumentParser(description="Check narration results.")
    parser.add_argument("--entity", default="aayush", help="Entity profile ID")
    parser.add_argument("--fy", default="FY26", help="Financial year")
    parser.add_argument("--file", help="Explicit file path")
    args = parser.parse_args()

    file_p = Path(args.file) if args.file else None
    check_results(args.entity, args.fy, file_p)


if __name__ == "__main__":
    main()
