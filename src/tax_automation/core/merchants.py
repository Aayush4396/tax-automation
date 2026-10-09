# -*- coding: utf-8 -*-
"""
merchants.py
============
Maps UPI merchant VPA keywords to narration labels, account heads, and
confidence scores, loaded dynamically from config/merchants.json.
"""

from __future__ import annotations
import re
from tax_automation.config_loader import get_merchants_config

# Load merchant configuration dynamically
_raw_merchants = get_merchants_config()

MERCHANT_MAP: list[tuple[str, tuple[str, str, float]]] = [
    (item["keyword"], (item["label"], item["account_head"], float(item["confidence"])))
    for item in _raw_merchants
]

_COMPILED: list[tuple[re.Pattern, tuple[str, str, float]]] = [
    (re.compile(re.escape(kw), re.IGNORECASE), val) for kw, val in MERCHANT_MAP
]


def detect_merchant(particulars: str) -> tuple[str, str, float] | None:
    """Scan the particulars text for a known merchant keyword."""
    p = str(particulars)
    for pattern, val in _COMPILED:
        if pattern.search(p):
            return val
    return None
