# -*- coding: utf-8 -*-
"""federal.py — Federal Bank (Jupiter) generic statement narration rules."""

from __future__ import annotations
import re

RULES_FEDERAL: list[tuple] = [
    # ── Bank Interest — SBINT credit ─────────────────────────────────────
    (
        "Bank Interest",
        "Bank Interest",
        lambda p, dr, cr: bool(re.search(r"SBINT:", p, re.IGNORECASE)) and cr > 0,
        0.96,
    ),
    # ── MF Redemption — Navi / NEOSIEXEDDD NFT credits ───────────────────
    (
        "MF Redemption",
        "Mutual Funds",
        lambda p, dr, cr: bool(
            re.search(r"NFT/NAVI\s*REDEMPTION|NFT/.*REDEMPTION", p, re.IGNORECASE)
        )
        and cr > 0,
        0.93,
    ),
    # ── SIP / MF Purchase — NFT / NEOSIEXEDDD debits ─────────────────────
    (
        "MF Investment",
        "Investments",
        lambda p, dr, cr: bool(
            re.search(r"NFT/\s*NEOSIEXEDDD|NFT/\s*(?:INVEST|SIP)", p, re.IGNORECASE)
        )
        and dr > 0,
        0.88,
    ),
    # ── Incoming fund transfer (IFN) — interest/misc ─────────────────────
    (
        "Misc Income",
        "Misc Income",
        lambda p, dr, cr: bool(re.search(r"^IFN/", p, re.IGNORECASE)) and cr > 0,
        0.60,
    ),
    # ── Internal / Operative account transfer ────────────────────────────
    (
        "Internal Transfer",
        "Transfer",
        lambda p, dr, cr: bool(re.search(r"Dr Operative A/c", p, re.IGNORECASE)),
        0.82,
    ),
]
