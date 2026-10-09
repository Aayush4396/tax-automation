# -*- coding: utf-8 -*-
"""rules_federal.py — Federal Bank (Jupiter) specific narration rules."""

from __future__ import annotations
import re

# Aayush's own UPI VPAs / IDs seen in Federal statement
_SELF_VPAS = ["aayush20g", "9594435259"]

RULES_FEDERAL: list[tuple] = [
    # ── Bank Interest — SBINT credit ─────────────────────────────────────
    (
        "Bank Interest",
        "Bank Interest",
        lambda p, dr, cr: bool(re.search(r"SBINT:", p, re.IGNORECASE)) and cr > 0,
        0.96,
    ),
    # ── Self Transfer inward ← KOTAK (UPI IN with self VPAs) ─────────────
    (
        "Contra - Kotak",
        "KOTAK 0333",
        lambda p, dr, cr: (
            bool(re.search(r"UPI\s*IN/", p, re.IGNORECASE))
            and any(vpa in p for vpa in _SELF_VPAS)
            and cr > 0
        ),
        0.90,
    ),
    # ── Self Transfer outward → KOTAK (UPIOUT with self VPAs) ────────────
    (
        "Contra - Kotak",
        "KOTAK 0333",
        lambda p, dr, cr: (
            bool(re.search(r"UPIOUT/", p, re.IGNORECASE))
            and any(vpa in p for vpa in _SELF_VPAS)
            and dr > 0
        ),
        0.90,
    ),
    # ── Self Transfer outward → SBI (UPIOUT, known SBI VPA / Contra) ─────
    (
        "Contra - SBI",
        "SBI 1227",
        lambda p, dr, cr: bool(
            re.search(r"UPIOUT/.*aayush20g|Dr Operative A/c", p, re.IGNORECASE)
        )
        and dr > 0,
        0.85,
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
