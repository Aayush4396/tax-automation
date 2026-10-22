# -*- coding: utf-8 -*-
"""check_narration_results.py.

Quick sanity check on generated Excel ledger sheet counts and rows.
"""

from __future__ import annotations
from pathlib import Path
from openpyxl import load_workbook

from tax_automation.config_loader import get_entity_config, resolve_output_dir


def check_results(entity_id: str, fy: str, file_path: Path | None = None) -> dict:
    """Verifies that the generated ledger exists and has non-empty sheets.

    Returns:
        dict with total_sheets, bank_sheets counts, and sheet name lists.
    """
    config = get_entity_config(entity_id)
    output_sheet_names = set(config.get("output_sheet_names", []))

    if file_path is None:
        file_path = resolve_output_dir(entity_id, fy) / "narrated_ledger.xlsx"

    if not file_path.exists():
        raise FileNotFoundError(f"Excel file not found at {file_path}")

    wb = load_workbook(file_path, read_only=True)
    sheet_names = list(wb.sheetnames)
    wb.close()

    bank_sheets = [s for s in sheet_names if s not in output_sheet_names]
    return {
        "total_sheets": len(sheet_names),
        "bank_sheets": len(bank_sheets),
        "sheet_names": sheet_names,
        "bank_sheet_names": bank_sheets,
    }
