# -*- coding: utf-8 -*-
"""
rules_hdfc.py
=============
HDFC Bank-specific narration rules. Applied BEFORE common rules.
"""

from __future__ import annotations
import re

# HDFC savings account number linked to HDFC Securities
_HSL_ACNO = "50200085415108"

RULES_HDFC: list[tuple] = [
    # ── HDFC Securities: BUY (NET PI = Pay-In to broker) ─────────────────
    (
        "HDFC Securities - Buy",
        "HDFC Securities",
        lambda p, dr, cr: bool(re.search(r"NET\s*PI\s*TO\s*HSL", p, re.IGNORECASE))
        and dr > 0,
        0.97,
    ),
    # ── HDFC Securities: SELL (NET PO = Pay-Out from broker) ─────────────
    (
        "HDFC Securities - Sell",
        "HDFC Securities",
        lambda p, dr, cr: bool(re.search(r"NET\s*PO\s*FROM\s*HSL", p, re.IGNORECASE))
        and cr > 0,
        0.97,
    ),
    # ── HDFC Securities: Fund Transfer / Settlement ───────────────────────
    (
        "HDFC Securities - Settlement",
        "HDFC Securities",
        lambda p, dr, cr: (
            bool(re.search(r"HDFC\s*SECURITIES\s*LTD", p, re.IGNORECASE))
            or (_HSL_ACNO in p and p.startswith("FT-"))
        ),
        0.93,
    ),
    # ── BSE/ICCL Settlement (Indian Clearing Corporation Ltd) ─────────────
    # NEFT CR-UTIB0000004-INDIAN CLEARING CORPORATION LTD-...
    # ICCL is the BSE clearing arm; credits = equity/MF trade settlement
    (
        "BSE Settlement",
        "HDFC Securities",
        lambda p, dr, cr: bool(
            re.search(
                r"INDIAN\s*CLEARING\s*CORP|ICCL|UTIB0000004.*CLEARING", p, re.IGNORECASE
            )
        )
        and cr > 0,
        0.93,
    ),
    # ── Bank Charges ──────────────────────────────────────────────────────
    (
        "Bank Charges",
        "Bank Charges",
        lambda p, dr, cr: bool(
            re.search(
                r"ISAQMC|INSTAALERTCHG|SMS\s*ALERT|Annual\s*Fee|CHRGS|MIN\s*BAL|"
                r"Chgs\s*Incl|MICR\s*CHG|STAMP\s*DUTY|MIR\d+|ISAQ",
                p,
                re.IGNORECASE,
            )
        )
        and dr > 0,
        0.90,
    ),
    # ── Depository Charges ────────────────────────────────────────────────
    (
        "Depository Charges",
        "Depository Charges",
        lambda p, dr, cr: bool(
            re.search(
                r"DEPOSITORY\s*CHARGES|DEMAT\s*CHG|DP\s*CHR[GS]", p, re.IGNORECASE
            )
        )
        and dr > 0,
        0.93,
    ),
    # ── SIP — INDIANESIGN mandate (BSE/IndianClearing) ───────────────────
    (
        "SIP",
        "SIP",
        lambda p, dr, cr: bool(
            re.search(
                r"ACH\s*D[- ]+TP\s*ACH\s*INDIANESIGN|INDIANESIGN", p, re.IGNORECASE
            )
        )
        and dr > 0,
        0.95,
    ),
    # ── SIP — BillDesk / Indian Clearing ────────────────────────────────
    (
        "SIP",
        "SIP",
        lambda p, dr, cr: bool(
            re.search(r"BILLDK|BILLDKINDIAN|NACHINDIANCLEARING", p, re.IGNORECASE)
        )
        and dr > 0,
        0.90,
    ),
    # ── Life Insurance Premium — HDFC Life (ACH debit) ────────────────────────
    (
        "Life Insurance Premium",
        "Life Insurance",
        lambda p, dr, cr: bool(
            re.search(r"ACH\s*D[- ]+HDFCLIFE|ACH\s*D[- ].*HDFCLIFE", p, re.IGNORECASE)
        )
        and dr > 0,
        0.95,
    ),
    # ── Life Insurance Premium — HDFC Life (other formats + NEFT HLIC INST) ───
    (
        "Life Insurance Premium",
        "Life Insurance",
        lambda p, dr, cr: bool(
            re.search(
                r"HDFCSTANDARDLIFE|HDFCLIFE|HDFC\s*STANDARD\s*LIFE|"
                r"HDFC\s*LIFE|HLIC[-_ ]*INST",
                p,
                re.IGNORECASE,
            )
        )
        and dr > 0,
        0.90,
    ),
    # ── Annuity Income — HDFCLIFE CENTR credit ───────────────────────────
    (
        "Annuity Income",
        "Annuity",
        lambda p, dr, cr: bool(re.search(r"HDFCLIFE\s*CENTR", p, re.IGNORECASE))
        and cr > 0,
        0.95,
    ),
    # ── Health Insurance ─────────────────────────────────────────────────
    (
        "Health Insurance",
        "Health Insurance",
        lambda p, dr, cr: bool(
            re.search(
                r"CARE\s*HEALTH|RELIGARE|STAR\s*HEALTH|NIVA\s*BUPA|"
                r"MAX\s*BUPA|MAXBUPA|BAJAJ\s*ALLIANZ",
                p,
                re.IGNORECASE,
            )
        )
        and dr > 0,
        0.92,
    ),
    # ── Dividend Income — ACH credit ─────────────────────────────────────
    (
        "Dividend Income",
        "Dividend Income",
        lambda p, dr, cr: bool(re.search(r"^ACH\s*C[- ]", p, re.IGNORECASE)) and cr > 0,
        0.88,
    ),
    # ── Dividend Income — company DIV credits ────────────────────────────
    (
        "Dividend Income",
        "Dividend Income",
        lambda p, dr, cr: bool(
            re.search(r"\bDIV\d*\b|\bDIVIDEND\b|\s+DIV\d+", p, re.IGNORECASE)
        )
        and cr > 0,
        0.85,
    ),
    # ── MF Redemption from AMCs ───────────────────────────────────────────
    (
        "MF Redemption",
        "Mutual Funds",
        lambda p, dr, cr: bool(
            re.search(
                r"INVESCO\s*MF|PPFAS|MIRAE|SBI\s*MF|HDFC\s*MF|AXIS\s*MF|CAMS|KFIN",
                p,
                re.IGNORECASE,
            )
        )
        and cr > 0,
        0.87,
    ),
    # ── Misc Income — IMPS credit ────────────────────────────────────────
    (
        "Misc Income",
        "Misc Income",
        lambda p, dr, cr: bool(re.search(r"^IMPS", p, re.IGNORECASE))
        and cr > 0
        and dr == 0,
        0.55,
    ),
    # ── Internal Transfer — HDFC -TPT- format ────────────────────────────────
    (
        "Internal Transfer",
        "Transfer",
        lambda p, dr, cr: (
            bool(re.search(r"-TPT-", p, re.IGNORECASE))
            and not bool(
                re.search(
                    r"SUNITA|AJAY|AAYUSH|ARCHIT|MEGHA|HUF|ISHWAR|PARADISE|MAINT",
                    p,
                    re.IGNORECASE,
                )
            )
        ),
        0.80,
    ),
    # ── NSE Clearing / MFSS Settlement (MF redemption credits) ────────────────
    (
        "MF Redemption",
        "Mutual Funds",
        lambda p, dr, cr: bool(
            re.search(r"NSE\s*CLEARING|MFSS\s*SETTLEMENT|NSE\s*MFSS", p, re.IGNORECASE)
        )
        and cr > 0,
        0.90,
    ),
    # ── HDBFSS (HDFC Bank Financial Services Settlement) ────────────────────
    (
        "Securities Settlement",
        "HDFC Securities",
        lambda p, dr, cr: bool(re.search(r"HDBFSS", p, re.IGNORECASE)),
        0.80,
    ),
    # ── JSW Cement IPO (ASBA / demat settlement) ──────────────────────────────
    (
        "IPO - JSW Cement",
        "Equities",
        lambda p, dr, cr: bool(re.search(r"JSWCEMENTG", p, re.IGNORECASE)) and dr > 0,
        0.92,
    ),
    # ── Tata Technologies IPO ──────────────────────────────────────────────
    (
        "IPO - Tata Tech",
        "Equities",
        lambda p, dr, cr: bool(re.search(r"TATAG", p, re.IGNORECASE)) and dr > 0,
        0.92,
    ),
    # ── JSW Infrastructure IPO ──────────────────────────────────────────────
    (
        "IPO - JSW Infra",
        "Equities",
        lambda p, dr, cr: bool(re.search(r"JSINFRA", p, re.IGNORECASE)) and dr > 0,
        0.92,
    ),
    # ── Aeroflex IPO ──────────────────────────────────────────────
    (
        "IPO - Aeroflex",
        "Equities",
        lambda p, dr, cr: bool(re.search(r"AEROFLEXG", p, re.IGNORECASE)) and dr > 0,
        0.92,
    ),
    # ── Lounge Access Charge (Travel Club / POS) ──────────────────────────
    (
        "Lounge Access Charge",
        "Bank Charges",
        lambda p, dr, cr: bool(
            re.search(
                r"TRAVEL\s*CLUB\s*LOUN|LOUNGE\s*ACCESS|LOUNGE\s*VISIT", p, re.IGNORECASE
            )
        ),
        0.80,
    ),
    # ── IPO Application (debit) ─────────────────────────────────────────
    # Pattern: TATACAPG/..., <COMPANY>G/..., UPI-IPO..., ASBA...
    (
        "IPO Application",
        "Equities",
        lambda p, dr, cr: (
            bool(
                re.search(
                    r"TATACAPG|HDFCBANKIPOG|SMBCG|BAJAJHFG|BHARATIHWNG|"
                    r"KFIN\s*IPO|LINKINTIME.*IPO|IPOREFUND|ASBAREFUND|"
                    r"\bIPO\b.*REFUND|UPI[/-]IPO",
                    p,
                    re.IGNORECASE,
                )
            )
            or bool(
                re.search(
                    r"/ASBA|ASBA/|ASBA\s*BLOCK|ASBA\s*UNBLOCK|" r"\bIPO\b",
                    p,
                    re.IGNORECASE,
                )
            )
        )
        and dr > 0,
        0.92,
    ),
    # ── IPO Refund (credit) ───────────────────────────────────────────────
    (
        "IPO Refund",
        "Equities",
        lambda p, dr, cr: (
            bool(
                re.search(
                    r"TATACAPG|IPOREFUND|ASBAREFUND|IPO.*REFUND|REFUND.*IPO|"
                    r"ASBA\s*UNBLOCK",
                    p,
                    re.IGNORECASE,
                )
            )
        )
        and cr > 0,
        0.92,
    ),
]
