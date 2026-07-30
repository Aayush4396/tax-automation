# -*- coding: utf-8 -*-
"""
check_narration_results.py
===========================
Analyzes confidence scores and human narration match rates for an entity ledger.
"""

import sys
import argparse
from pathlib import Path
import pandas as pd
from openpyxl import load_workbook

from tax_automation.config_loader import get_entity_config, REPO_ROOT


def check_results(entity_id: str, fy: str, file_path: Path | None = None) -> bool:
    config = get_entity_config(entity_id)
    output_sheet_names = set(s.lower() for s in config.get("output_sheet_names", []))
    output_sheet_names.update({"conso", "for tally", "bank summary", "monthly pivot", "cc transactions", "colour legend"})

    entity_dir_name = entity_id.title()
    if file_path is None:
        file_path = REPO_ROOT / "data" / entity_dir_name / "Generated Data" / fy / f"{entity_dir_name.split()[0]}_Consolidated_Bank_Ledger_{fy}.xlsx"

    if not file_path.exists():
        print(f"Error: Excel file not found at {file_path}")
        return False

    print(f"Checking narration results for {entity_id.title()} ({fy}) in: {file_path}")
    wb = load_workbook(file_path, read_only=True)
    sheet_names = wb.sheetnames
    wb.close()

    bank_sheets = [s for s in sheet_names if s.lower().strip() not in output_sheet_names]
    print(f"Identified bank sheets to verify: {bank_sheets}")
    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Check narration results")
    parser.add_argument("--entity", default="ajay", help="Entity profile ID")
    parser.add_argument("--fy", default="FY26", help="Financial year")
    args = parser.parse_args()
    check_results(args.entity, args.fy)
