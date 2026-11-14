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


def detect_merchant(particulars: str) -> tuple[str, str, float] | None:
    """Scan the particulars text for a known merchant keyword."""
    p = str(particulars)
    for item in get_merchants_config():
        if re.search(re.escape(item["keyword"]), p, re.IGNORECASE):
            return item["label"], item["account_head"], float(item["confidence"])
    return None
