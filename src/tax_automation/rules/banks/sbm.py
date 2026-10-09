# -*- coding: utf-8 -*-
"""rules_sbm.py — SBM Bank-specific narration rules (interest-only account)."""

from __future__ import annotations
import re

RULES_SBM: list[tuple] = [
    # ── Self-transfer outward to Kotak ──────────────────────────────────
    (
        "Contra - Kotak",
        "KOTAK 0333",
        lambda p, dr, cr: bool(re.search(r"STCB010825236957", p)) and dr > 0,
        0.90,
    ),
    # ── Bank Interest — only meaningful pattern in this account ───────────
    (
        "Bank Interest",
        "Bank Interest",
        lambda p, dr, cr: bool(re.search(r"Int\.Pd|INTEREST\s*PAID", p, re.IGNORECASE))
        and cr > 0,
        0.97,
    ),
]
