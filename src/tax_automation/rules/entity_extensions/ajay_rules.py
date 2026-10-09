# -*- coding: utf-8 -*-
"""
ajay_rules.py
=============
Entity-specific classification rules for Ajay. Appended before bank base rules.
"""

from __future__ import annotations
import re

EXTRA_RULES: dict[str, list[tuple]] = {
    "common": [
        (
            "Transfer - Ajay Kumar Gupta - HUF",
            "Ajay Gupta HUF",
            lambda p, dr, cr: bool(
                re.search(r"\bHUF\b|\bH\.U\.F\.\b", p, re.IGNORECASE)
            ),
            0.90,
        ),
    ],
    "hdfc": [],
    "kotak": [],
    "sbi": [],
}
