# -*- coding: utf-8 -*-
"""
aayush_rules.py
===============
Entity-specific classification rules for Aayush. Appended before bank base rules.
"""

from __future__ import annotations
import re

EXTRA_RULES: dict[str, list[tuple]] = {
    "common": [
        (
            "Contra - SBI",
            "SBI 1227",
            lambda p, dr, cr: bool(re.search(r"\bAAYUSH\b", p, re.IGNORECASE))
            and bool(
                re.search(r"STATE\s*BANK\s*OF\s*INDIA|SBI\b|SBIN", p, re.IGNORECASE)
            ),
            0.90,
        ),
        (
            "Contra - Kotak",
            "KOTAK 0333",
            lambda p, dr, cr: bool(re.search(r"\bAAYUSH\b", p, re.IGNORECASE))
            and bool(re.search(r"KOTAK\b|KKBK", p, re.IGNORECASE)),
            0.90,
        ),
        (
            "Contra - Jupiter",
            "FEDERAL 0847",
            lambda p, dr, cr: bool(re.search(r"\bAAYUSH\b", p, re.IGNORECASE))
            and bool(re.search(r"JUPITER|FEDERAL\b|FDRL", p, re.IGNORECASE)),
            0.90,
        ),
        (
            "Contra - Axis",
            "Axis",
            lambda p, dr, cr: bool(re.search(r"\bAAYUSH\b", p, re.IGNORECASE))
            and bool(re.search(r"AXIS\b|UTIB", p, re.IGNORECASE)),
            0.90,
        ),
        (
            "Contra - HDFC",
            "HDFC 5413",
            lambda p, dr, cr: (
                bool(re.search(r"\bAAYUSH\b", p, re.IGNORECASE))
                and bool(re.search(r"HDFC", p, re.IGNORECASE))
                and not bool(
                    re.search(
                        r"HDFC\s*SECURITIES|HDBFSS|HDFCLIFE|HDFC\s*MF|"
                        r"HDFC\s*MUTUAL\s*FUND|HDFCMF",
                        p,
                        re.IGNORECASE,
                    )
                )
            ),
            0.90,
        ),
        (
            "Contra - SBM",
            "SBM",
            lambda p, dr, cr: bool(re.search(r"\bAAYUSH\b", p, re.IGNORECASE))
            and bool(re.search(r"SBM\b|STCB", p, re.IGNORECASE)),
            0.90,
        ),
    ],
    "hdfc": [],
    "kotak": [],
    "sbi": [],
}
