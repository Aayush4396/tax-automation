# -*- coding: utf-8 -*-
"""
rules_boi.py
============
Bank of India-specific narration rules. Applied BEFORE common rules.
"""

from __future__ import annotations
import re

RULES_BOI: list[tuple] = [
    # ── Bank Interest ─────────────────────────────────────────────────────
    (
        "Bank Interest",
        "Bank Interest",
        lambda p, dr, cr: bool(re.search(r"SBInt\.Pd", p, re.IGNORECASE)) and cr > 0,
        0.95,
    ),
]
