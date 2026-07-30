# -*- coding: utf-8 -*-
"""
rules_kotak.py
==============
Kotak Mahindra Bank-specific narration rules. Applied BEFORE common rules.
"""
from __future__ import annotations
import re
from narration_engine.bank_registry import (
    SELF_UPI_REFS_JUPITER, SELF_UPI_REFS_SBI,
)

RULES_KOTAK: list[tuple] = [

    # ── Bank Interest ─────────────────────────────────────────────────────
    (
        "Bank Interest", "Bank Interest",
        lambda p, dr, cr: bool(re.search(
            r"Int\.Pd[:.]|INTEREST\s*PAID|INT\s*PD\b",
            p, re.IGNORECASE)),      # Kotak Int.Pd: is always a credit; don't require cr>0
        0.95,
    ),

    # ── Bank Charges — Kotak Chrg: format ────────────────────────────────
    # ECS Return for HDFC Life (insufficient funds) — NOT a bank charge;
    # it's a return charge because the premium debit bounced.
    (
        "Premium Payment (ECS Return Charge)", "Life Insurance",
        lambda p, dr, cr: bool(re.search(
            r"Chrg:\s*ECS\s*Return.*HDFC\s*Life|ECS\s*Return.*HDFCLife",
            p, re.IGNORECASE)) and dr > 0,
        0.93,
    ),

    (
        "Bank Charges", "Bank Charges",
        lambda p, dr, cr: bool(re.search(
            r"^Chrg:|Chgs:|Charges|Annual\s*Fee|SMS\s*Alert|Min\s*Bal|GST\s*ON",
            p, re.IGNORECASE)),
        0.88,
    ),

    # ── Tibil F&F — Tibil Computers Ltd one-time FnF ─────────────────────
    # Specific amount: 91056 credit
    (
        "Salary", "Salary",
        lambda p, dr, cr: bool(re.search(r"^TRANS$", p.strip(), re.IGNORECASE)) and cr == 91056,
        0.85,
    ),

    # ── Internal TRANS / sweep ────────────────────────────────────────────
    (
        "Auto Sweep FD", "Auto Sweep FD",
        lambda p, dr, cr: bool(re.search(r"^TRANS$", p.strip(), re.IGNORECASE)) and not (cr == 91056),
        0.75,
    ),

    # ── Zerodha Coin (Mutual Fund investment via ICCL) ──────────────────────
    (
        "MF Investment", "Investments",
        lambda p, dr, cr: bool(re.search(r"iccl", p, re.IGNORECASE)) and dr > 0,
        0.90,
    ),

    # ── Zerodha Broking (exclude NACH-MUT-DR / ICCL which are MF investments) ──
    (
        "Zerodha Broking", "Zerodha Broking Limited",
        lambda p, dr, cr: (
            bool(re.search(r"ZERODHA", p, re.IGNORECASE))
            and not bool(re.search(r"NACH[- ]MUT[- ]DR|ICCL", p, re.IGNORECASE))
        ),
        0.92,
    ),

    # ── SIP — NACH-MUT-DR (Kotak mutual fund NACH mandate) ───────────────
    (
        "SIP", "SIP",
        lambda p, dr, cr: bool(re.search(r"NACH[- ]MUT[- ]DR", p, re.IGNORECASE)) and dr > 0,
        0.96,
    ),

    # ── SIP — PG INDIAN CLEARING CORP / PG FOR QUANT / PG INVESTMENT ─────
    (
        "MF Investment", "Investments",
        lambda p, dr, cr: bool(re.search(
            r"PG\s+(?:INDIAN\s+CLEARING|FOR\s+\w+|INVESTMENT)",
            p, re.IGNORECASE)) and dr > 0,
        0.88,
    ),

    # ── Dividend — NACH-ECS-CR ────────────────────────────────────────────
    (
        "Dividend Income", "Dividend Income",
        lambda p, dr, cr: bool(re.search(r"NACH[- ]ECS[- ]CR", p, re.IGNORECASE)) and cr > 0,
        0.93,
    ),

    # ── Dividend — NACH-10-CR format (newer Kotak) ───────────────────────
    (
        "Dividend Income", "Dividend Income",
        lambda p, dr, cr: bool(re.search(r"NACH[- ]10[- ]CR[- ]", p, re.IGNORECASE)) and cr > 0,
        0.93,
    ),

    # ── Dividend — DIV keyword or IDIV / FNLDIV in description ──────────
    (
        "Dividend Income", "Dividend Income",
        lambda p, dr, cr: bool(re.search(
            r"\bDIV\b|\bDIVIDEND\b|\bIDIV\d*\b|FNLDIV|INTDIV|\bNACH-ECS-CR\b|\bNACH-10-CR\b",
            p, re.IGNORECASE)),       # Kotak Amount+Dr/Cr format: cr may be 0 in raw parse
        0.85,
    ),

    # ── Self Transfer → Jupiter (Federal) — known UPI refs ───────────────
    (
        "Contra - Jupiter", "FEDERAL 0847",
        lambda p, dr, cr: (
            bool(re.search(r"AAYUSH\s*KUMAR\s*GU", p, re.IGNORECASE))
            and any(ref in p for ref in SELF_UPI_REFS_JUPITER)
            and dr > 0
        ),
        0.90,
    ),
    (
        "Contra - Jupiter (Inward)", "FEDERAL 0847",
        lambda p, dr, cr: (
            bool(re.search(r"AAYUSH\s*KUMAR\s*GU", p, re.IGNORECASE))
            and any(ref in p for ref in SELF_UPI_REFS_JUPITER)
            and cr > 0
        ),
        0.90,
    ),

    # ── Self Transfer → SBI — known UPI refs ─────────────────────────────
    (
        "Contra - SBI", "SBI 1227",
        lambda p, dr, cr: (
            bool(re.search(r"AAYUSH\s*KUMAR\s*GU", p, re.IGNORECASE))
            and any(ref in p for ref in SELF_UPI_REFS_SBI)
        ),
        0.90,
    ),

    # ── Self Transfer inward from Federal (FDRL NEFT) ────────────────────
    (
        "Contra - Jupiter", "FEDERAL 0847",
        lambda p, dr, cr: bool(re.search(
            r"FDRL[A-Z0-9]+\s+CURRENT\s+ACCOUNT|FEDERAL\s+BANK",
            p, re.IGNORECASE)) and cr > 0,
        0.85,
    ),

    # ── Rent — Nagaraj / Nelaballi / landlord names ───────────────────────
    (
        "Rent", "Rent",
        lambda p, dr, cr: bool(re.search(
            r"NELABALLI|NAGARAJ\s*A|PG\s*FEE[S]?\b|PG\s*RENT|\bRENT\b",
            p, re.IGNORECASE)) and dr > 0,
        0.88,
    ),

    # ── ATM / Cash Withdrawal (ATL/ ATW/ format) ─────────────────────────
    (
        "Cash Withdrawal", "Cash",
        lambda p, dr, cr: bool(re.search(
            r"^ATL/|^ATW/|CASH\s*WITHD|CWDR",
            p, re.IGNORECASE)) and dr > 0,
        0.92,
    ),

    # ── Card Purchase (PCD/ debit card POS) ──────────────────────────────
    (
        "Card Purchase", "Personal",
        lambda p, dr, cr: bool(re.search(r"^PCD/", p, re.IGNORECASE)) and dr > 0,
        0.88,
    ),

    # ── Credit Card Payment (MB:PAID CARD) ───────────────────────────────
    (
        "Credit Card Payment", "Personal",
        lambda p, dr, cr: bool(re.search(
            r"^MB:PAID\s*CARD|CREDIT\s*CARD\s*PAY",
            p, re.IGNORECASE)) and dr > 0,
        0.90,
    ),

    # ── CDSL / Depository credit ──────────────────────────────────────────
    (
        "Depository Credit", "CDSL",
        lambda p, dr, cr: bool(re.search(
            r"CENTRAL\s*DEPOSITORY|CDSL|NSDL\s*DEPOS",
            p, re.IGNORECASE)) and cr > 0,
        0.90,
    ),

    # ── MF Refund / PG RETURN ────────────────────────────────────────────
    (
        "MF Refund / Reversal", "Mutual Funds",
        lambda p, dr, cr: bool(re.search(r"PG\s+RETURN|RETURN\s+NK", p, re.IGNORECASE)),
        0.80,
    ),

    # ── IMPS Receipt ─────────────────────────────────────────────────────
    (
        "IMPS Receipt", "Personal",
        lambda p, dr, cr: bool(re.search(r"^Recd:IMPS|^IMPS\s*IN", p, re.IGNORECASE)) and cr > 0,
        0.72,
    ),

    # ── IPO — Billion Garages (Groww / Billionbrains Garage Ventures) ─────────
    # Groww's legal entity is Billionbrains Garage Ventures Pvt Ltd.
    # UPI ASBA mandate shows 'UPIM/Billionbrains Garage/<ref>'
    (
        "IPO - Billion Garages", "Equities",
        lambda p, dr, cr: bool(re.search(r"Billionbrains\s*Garage|BILLIONBRAINS", p, re.IGNORECASE)) and dr > 0,
        0.97,
    ),

    # ── UPI Reversal ─────────────────────────────────────────────────────
    (
        "UPI Reversal", "Personal",
        lambda p, dr, cr: bool(re.search(r"^REV[-/]UPI|UPI_CRADJ", p, re.IGNORECASE)),
        0.88,
    ),
]
