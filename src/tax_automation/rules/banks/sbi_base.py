# -*- coding: utf-8 -*-
"""sbi_base.py — State Bank of India generic statement narration rules."""

from __future__ import annotations
import re

RULES_SBI: list[tuple] = [
    # ── Dividend Income — BULK POSTING (SBI format, ACHCr / C prefix) ─────────
    (
        "Dividend Income",
        "Dividend Income",
        lambda p, dr, cr: bool(
            re.search(r"BULK\s*POSTING[-\s]*(?:ACHCr|C\d+)", p, re.IGNORECASE)
        )
        and cr > 0,
        0.88,
    ),
    # ── Bank Interest — CREDIT INTEREST (SBI format) ─────────────────────────
    (
        "Bank Interest",
        "Bank Interest",
        lambda p, dr, cr: bool(
            re.search(r"CREDIT\s*INTEREST|INT(?:EREST)?\s*CREDIT", p, re.IGNORECASE)
        )
        and cr > 0,
        0.92,
    ),
    # ── Life Insurance Premium — INB Insurance / HDFC Life ───────────────────
    (
        "Life Insurance Premium",
        "Life Insurance",
        lambda p, dr, cr: bool(
            re.search(
                r"INB\s*HDFC\s*LIFE|INB.*INSURANCE|HDFC\s*LIFE\s*INSUR|LIC\s*PREMIUM",
                p,
                re.IGNORECASE,
            )
        )
        and dr > 0,
        0.88,
    ),
    # ── PPF Deposit — SBI Internet Banking PPF Transfer ───────────────────────
    (
        "PPF Deposit",
        "PPF Deposit",
        lambda p, dr, cr: (
            bool(re.search(r"SBIYA.*PPF|INB.*PPF|\bPPF\b", p, re.IGNORECASE))
        )
        and dr > 0,
        0.88,
    ),
    # ── Auto Sweep / Term Deposit — SBI Sweep & MOD ───────────────────────────
    (
        "Auto Sweep FD",
        "Auto Sweep FD",
        lambda p, dr, cr: bool(
            re.search(
                r"INB\s*Deposit|INB\s*Investment|INB\s*Dep|Deposit\s*or\s*Inv|SBIYA|"
                r"SWEEP\s*TRF|MOD\s*REFUND|AUTO\s*SWEEP",
                p,
                re.IGNORECASE,
            )
        )
        and dr > 0,
        0.85,
    ),
    # ── Bank Charges — SBI Format ─────────────────────────────────────────────
    (
        "Bank Charges",
        "Bank Charges",
        lambda p, dr, cr: bool(
            re.search(
                r"^CHG:|^CHARGES|SMS\s*CHG|MIN\s*BAL\s*CHG|ANNUAL\s*MAINT",
                p,
                re.IGNORECASE,
            )
        )
        and dr > 0,
        0.88,
    ),
    # ── ATM / Cash Withdrawal — SBI Format ───────────────────────────────────
    (
        "ATM Withdrawal",
        "Cash Withdrawal",
        lambda p, dr, cr: bool(
            re.search(r"ATM\s*WDL|ATM\s*CASH|CASH\s*WDL\s*ATM", p, re.IGNORECASE)
        )
        and dr > 0,
        0.90,
    ),
]
