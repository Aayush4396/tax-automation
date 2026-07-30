# -*- coding: utf-8 -*-
"""rules_axis.py — Axis Bank-specific narration rules."""
from __future__ import annotations
import re

RULES_AXIS: list[tuple] = [

    # ── Auto Sweep to/from FD ─────────────────────────────────────────────
    (
        "Auto Sweep FD", "Auto Sweep FD",
        lambda p, dr, cr: bool(re.search(
            r"AUTOSWEEP|SWEEP\s*TRF|REV\s*SWEEP",
            p, re.IGNORECASE)),
        0.95,
    ),

    # ── Bank Charges ──────────────────────────────────────────────────────
    (
        "Bank Charges", "Bank Charges",
        lambda p, dr, cr: bool(re.search(
            r"Chrgs|Charge|Alert\s*Fee|Min\s*Bal|ISAQ|SMS\s*Alert|"
            r"Annual\s*Fee|Chgs|GST\s*ON",
            p, re.IGNORECASE)) and dr > 0,
        0.88,
    ),

    # ── Bank Interest ─────────────────────────────────────────────────────
    (
        "Bank Interest", "Bank Interest",
        lambda p, dr, cr: (
            bool(re.search(r"Int\.Pd|SB:", p, re.IGNORECASE))
            or p.upper().startswith("SB:")
        ) and cr > 0,
        0.93,
    ),

    # ── SIP — ACH Debit ───────────────────────────────────────────────────
    (
        "SIP", "SIP",
        lambda p, dr, cr: bool(re.search(r"ACH\s*D[- ]|ECS\s*D\b", p, re.IGNORECASE)) and dr > 0,
        0.85,
    ),

    # ── Dividend / ACH Credit ─────────────────────────────────────────────
    (
        "Dividend Income", "Dividend Income",
        lambda p, dr, cr: bool(re.search(r"ACH\s*C[- ]|ECS\s*C\b", p, re.IGNORECASE)) and cr > 0,
        0.82,
    ),

    # ── Cheque Clearing ───────────────────────────────────────────────────
    (
        "Cheque", "Transfer",
        lambda p, dr, cr: bool(re.search(r"\bCLG\b|\bCHEQUE\b|\bCHQ\b|\bCTS\b", p, re.IGNORECASE)),
        0.80,
    ),

    # ── Mutual Funds / CAMS ───────────────────────────────────────────────
    (
        "MF Redemption", "Mutual Funds",
        lambda p, dr, cr: bool(re.search(
            r"\bMF\b|MUTUAL\s*FUND|CAMS|KARVY|KFINTECH|INVESCO\s*MF|"
            r"AXIS\s*MF|SBI\s*MF|HDFC\s*MF|MIRAE|PPFAS",
            p, re.IGNORECASE)) and cr > 0,
        0.82,
    ),

]
