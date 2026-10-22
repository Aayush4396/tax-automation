# -*- coding: utf-8 -*-
"""utils.py.

Shared utility functions for numerical conversion, formatting, and text sanitization.
"""

from __future__ import annotations
from typing import Any
import pandas as pd


def safe_float(val: Any) -> float:
    """Convert value to float safely, returning 0.0 for invalid values or NaN."""
    if pd.isna(val) or val is None:
        return 0.0
    try:
        val_str = str(val).replace(",", "").strip()
        return float(val_str)
    except (ValueError, TypeError):
        return 0.0
