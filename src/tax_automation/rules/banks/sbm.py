# -*- coding: utf-8 -*-
"""sbm.py — SBM Bank generic narration rules."""

from __future__ import annotations
import re

RULES_SBM: list[tuple] = [
    # ── Bank Interest ─────────────────────────────────────────────────────────
    (
        "Bank Interest",
        "Bank Interest",
        lambda p, dr, cr: bool(re.search(r"Int\.Pd|INTEREST\s*PAID", p, re.IGNORECASE))
        and cr > 0,
        0.97,
    ),
]
