# -*- coding: utf-8 -*-
"""parse_narration_stats.py.

Parses generated Excel ledger and displays classification confidence statistics.
"""

from __future__ import annotations
from pathlib import Path
import pandas as pd

from tax_automation.config_loader import resolve_output_dir


def get_narration_stats(filepath: Path, fy: str) -> dict:
    """Parses confidence statistics from a narrated ledger.

    Returns:
        dict with total, high/med/low transaction counts and percentages.
    """
    if not filepath.exists():
        raise FileNotFoundError(f"File not found: {filepath}")

    xl = pd.ExcelFile(filepath)
    exclude = {"Conso", "For Tally", "Bank Summary", "Monthly Pivot", "Guidelines"}
    sheet_names = [s for s in xl.sheet_names if s not in exclude]

    dfs = [xl.parse(s) for s in sheet_names]
    if not dfs:
        return {"total": 0, "high": 0, "med": 0, "low": 0}

    full_df = pd.concat(dfs, ignore_index=True)
    total = len(full_df)

    if "Confidence" not in full_df.columns:
        return {
            "total": total,
            "high": 0,
            "med": 0,
            "low": 0,
            "note": "No Confidence column",
        }

    high = int(len(full_df[full_df["Confidence"] >= 0.85]))
    med = int(
        len(full_df[(full_df["Confidence"] >= 0.60) & (full_df["Confidence"] < 0.85)])
    )
    low = int(len(full_df[full_df["Confidence"] < 0.60]))

    return {
        "fy": fy,
        "total": total,
        "high_confidence": {
            "count": high,
            "pct": round(high / total * 100, 1) if total else 0,
        },
        "med_confidence": {
            "count": med,
            "pct": round(med / total * 100, 1) if total else 0,
        },
        "low_confidence": {
            "count": low,
            "pct": round(low / total * 100, 1) if total else 0,
        },
    }


def resolve_ledger_path(entity_id: str, fy: str) -> Path:
    """Returns the canonical ledger path."""
    return resolve_output_dir(entity_id, fy) / "narrated_ledger.xlsx"
