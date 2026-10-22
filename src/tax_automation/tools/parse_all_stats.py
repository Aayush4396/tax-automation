# -*- coding: utf-8 -*-
"""parse_all_stats.py.

Parses Bank Summary sheet of the generated master Excel ledger.
"""

from __future__ import annotations
from pathlib import Path
import pandas as pd

from tax_automation.config_loader import resolve_output_dir


def parse_bank_summary(filepath: Path) -> list[dict]:
    """Parses the Bank Summary sheet from the narrated ledger.

    Returns:
        List of row dicts from the Bank Summary sheet.
    """
    if not filepath.exists():
        raise FileNotFoundError(f"File not found: {filepath}")

    xl = pd.ExcelFile(filepath)
    if "Bank Summary" not in xl.sheet_names:
        raise ValueError("Bank Summary sheet not found in workbook")

    df = xl.parse("Bank Summary", skiprows=4)
    df = df.dropna(how="all")
    return df.to_dict(orient="records")


def resolve_ledger_path(entity_id: str, fy: str) -> Path:
    """Returns the canonical ledger path."""
    return resolve_output_dir(entity_id, fy) / "narrated_ledger.xlsx"
