# -*- coding: utf-8 -*-
"""parse_narration_stats.py.

Parses generated Excel ledger and displays classification confidence statistics.
"""

from __future__ import annotations
from pathlib import Path
import pandas as pd

from tax_automation.config_loader import (
    get_exporter_theme_config,
    get_scoring_config,
    resolve_output_dir,
)


def get_narration_stats(filepath: Path, fy: str) -> dict:
    """Parses confidence statistics from a narrated ledger.

    Returns:
        dict with total, high/med/low transaction counts and percentages.
    """
    if not filepath.exists():
        raise FileNotFoundError(f"File not found: {filepath}")

    theme_cfg = get_exporter_theme_config()
    output_sheets_map = theme_cfg.get("output_sheets", {})
    default_excludes = set(
        theme_cfg.get(
            "default_output_sheet_names",
            [
                "Conso",
                "For Tally",
                "Bank Summary",
                "Monthly Pivot",
                "Colour Legend",
                "Guidelines",
            ],
        )
    ) | set(output_sheets_map.values())

    xl = pd.ExcelFile(filepath)
    sheet_names = [s for s in xl.sheet_names if s not in default_excludes]

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

    bands = get_scoring_config().get("confidence_bands", {})
    hi = float(bands.get("high", 0.85))
    lo = float(bands.get("medium_low", 0.60))

    high = int(len(full_df[full_df["Confidence"] >= hi]))
    med = int(
        len(full_df[(full_df["Confidence"] >= lo) & (full_df["Confidence"] < hi)])
    )
    low = int(len(full_df[full_df["Confidence"] < lo]))

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
