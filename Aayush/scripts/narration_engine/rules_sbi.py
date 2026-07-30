# -*- coding: utf-8 -*-
"""rules_sbi.py — State Bank of India-specific narration rules."""
from __future__ import annotations
import re
from narration_engine.bank_registry import SELF_UPI_REFS_SBI, RENT_VBAS_SBI

RULES_SBI: list[tuple] = [

    # ── Rent — known landlord VPA ─────────────────────────────────────────
    (
        "Rent", "Rent",
        lambda p, dr, cr: (
            any(vba in p for vba in RENT_VBAS_SBI)
            or bool(re.search(r"\bRENT\b|NELABALLI|NAGARAJ", p, re.IGNORECASE))
        ) and dr > 0,
        0.90,
    ),

    # ── Self Transfer outward → KOTAK (UPI/DR with known refs) ───────────
    (
        "Contra - Kotak", "KOTAK 0333",
        lambda p, dr, cr: (
            bool(re.search(r"UPI/DR/|TO TRANSFER.UPI/DR/", p, re.IGNORECASE))
            and any(ref in p for ref in SELF_UPI_REFS_SBI)
        ),
        0.88,
    ),

    # ── Self Transfer inward ← KOTAK (UPI/CR with known refs) ────────────
    (
        "Contra - Kotak", "KOTAK 0333",
        lambda p, dr, cr: (
            bool(re.search(r"UPI/CR/|BY TRANSFER.UPI/CR/", p, re.IGNORECASE))
            and any(ref in p for ref in SELF_UPI_REFS_SBI)
        ),
        0.88,
    ),



    # ── Dividend Income — BULK POSTING (SBI format, both ACHCr and C prefix) ──
    (
        "Dividend Income", "Dividend Income",
        lambda p, dr, cr: bool(re.search(
            r"BULK\s*POSTING[-\s]*(?:ACHCr|C\d+)",
            p, re.IGNORECASE)) and cr > 0,
        0.85,
    ),

    # ── Bank Interest — CREDIT INTEREST (SBI format) ────────────────────
    (
        "Bank Interest", "Bank Interest",
        lambda p, dr, cr: bool(re.search(
            r"CREDIT\s*INTEREST|INT(?:EREST)?\s*CREDIT",
            p, re.IGNORECASE)) and cr > 0,
        0.90,
    ),

    # ── Life Insurance Premium — INB HDFC Life / insurance via SBI IB ──────────
    (
        "Life Insurance Premium", "Life Insurance",
        lambda p, dr, cr: bool(re.search(
            r"INB\s*HDFC\s*LIFE|INB.*INSURANCE|HDFC\s*LIFE\s*INSUR",
            p, re.IGNORECASE)) and dr > 0,
        0.88,
    ),

    # ── PPF Deposit — SBI Internet Banking PPF Transfer ──────────────────
    (
        "SBI PPF", "PPF Deposit",
        lambda p, dr, cr: (
            bool(re.search(r"SBIYA|Deposit\s*or\s*Inv", p, re.IGNORECASE))
            and bool(re.search(r"0039706\s*255133", p))
        ) and dr > 0,
        0.90,
    ),

    # ── INB Deposit / Investment — SBI Internet Banking FD ────────────────
    (
        "Auto Sweep FD", "Auto Sweep FD",
        lambda p, dr, cr: bool(re.search(
            r"INB\s*Deposit|INB\s*Investment|INB\s*Dep|Deposit\s*or\s*Inv|SBIYA",
            p, re.IGNORECASE)) and dr > 0,
        0.82,
    ),
]

