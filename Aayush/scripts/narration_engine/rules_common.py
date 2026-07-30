# -*- coding: utf-8 -*-
"""
rules_common.py
===============
Cross-bank narration rules applied to ALL banks, after bank-specific rules.

Rule tuple format: (label, account_head, match_fn(p, dr, cr) -> bool, confidence)

Priority: top → bottom, first match wins.
The final rule is always the fallback: "What is this?"
"""

from __future__ import annotations
import re

RULES_COMMON: list[tuple] = [

    # ── Custom User Request Mappings (MAPPINGS 1–10) ─────────────────────────
    # 1. HUF Transfer (narrate as "Ajay Kumar Gupta - HUF", Account Head = "Ajay Gupta HUF")
    (
        "Transfer - Ajay Kumar Gupta - HUF", "Ajay Gupta HUF",
        lambda p, dr, cr: bool(re.search(r"\bHUF\b|\bH\.U\.F\.\b", p, re.IGNORECASE)),
        0.90,
    ),
    # SIP / Reversals
    (
        "SIP", "SIP",
        lambda p, dr, cr: bool(re.search(r"INDIANESIGN", p, re.IGNORECASE)),
        0.95,
    ),
    # IRCTC Rail Booking
    (
        "IRCTC Ticket Booking", "Travel",
        lambda p, dr, cr: bool(re.search(r"IRCTC|I\.R\.C\.T\.C\.|CRIS\s*RAIL|RAIL\s*CONNECT", p, re.IGNORECASE)) and dr > 0,
        0.95,
    ),
    # CEMTEX / Corporate Dividends -> Dividend Income
    (
        "Dividend Income", "Dividend Income",
        lambda p, dr, cr: bool(re.search(r"CEMTEX", p, re.IGNORECASE)) and cr > 0,
        0.95,
    ),
    # 3. Abhinandan Cloth Merchant is Anil Kumar Gupta
    (
        "Abhinandan Cloth Merchant", "Anil Kumar Gupta",
        lambda p, dr, cr: bool(re.search(r"AB[HF]INANDAN\s*CLOTH", p, re.IGNORECASE)),
        0.95,
    ),
    # 5. SBI Securities / SBI Cap Securities
    (
        "SBI Securities - Charges", "SBI Securities",
        lambda p, dr, cr: bool(re.search(r"SBICAP|SBI\s*CAPS?|SBI\s*CAP\s*SECURITIES", p, re.IGNORECASE)) and bool(re.search(r"Demat\s*Charges|Charges", p, re.IGNORECASE)) and dr > 0,
        0.95,
    ),
    (
        "SBI Securities - Buy", "SBI Securities",
        lambda p, dr, cr: bool(re.search(r"SBICAP|SBI\s*CAPS?|SBI\s*CAP\s*SECURITIES", p, re.IGNORECASE)) and dr > 0,
        0.92,
    ),
    (
        "SBI Securities - Sell", "SBI Securities",
        lambda p, dr, cr: bool(re.search(r"SBICAP|SBI\s*CAPS?|SBI\s*CAP\s*SECURITIES", p, re.IGNORECASE)) and cr > 0,
        0.92,
    ),
    # 6. SBI OD Interest Debit ("TO INTEREST") -> Bank Interest
    (
        "Bank Interest", "Bank Interest",
        lambda p, dr, cr: bool(re.search(r"\bTO\s*INTEREST\b", p, re.IGNORECASE)) and dr > 0,
        0.95,
    ),
    # 7. Sanofi Dividend Income
    (
        "Sanofi Dividend", "Dividend Income",
        lambda p, dr, cr: bool(re.search(r"Sanofi", p, re.IGNORECASE)) and cr > 0,
        0.95,
    ),
    # 8. HDFC Managed Customer Benefit (CGST/SGST) -> Bank Charges
    (
        "Bank Charges", "Bank Charges",
        lambda p, dr, cr: bool(re.search(r"MANAGED\s*CUSTOMER\s*BENEFIT|NCB\d{10,}", p, re.IGNORECASE)),
        0.92,
    ),
    # 9. Maruti Insurance -> Car Insurance
    (
        "Maruti Insurance", "Car Insurance",
        lambda p, dr, cr: bool(re.search(r"MARUTI\s*INSURANCE", p, re.IGNORECASE)) and dr > 0,
        0.95,
    ),
    # 10. Jio Postpaid Bill -> Personal
    (
        "Jio Postpaid Bill", "Personal",
        lambda p, dr, cr: bool(re.search(r"Jio\s*Postpaid|Jio\s*Bill", p, re.IGNORECASE)) and dr > 0,
        0.92,
    ),
    # 10. NSDL Charges -> Personal
    (
        "NSDL Charges", "Personal",
        lambda p, dr, cr: bool(re.search(r"NSDL", p, re.IGNORECASE)) and dr > 0,
        0.92,
    ),
    # 10. Techprocess Transfer -> Personal
    (
        "Techprocess Transfer", "Personal",
        lambda p, dr, cr: bool(re.search(r"TECHPROCESS", p, re.IGNORECASE)),
        0.92,
    ),

    # ── Salary — Mphasis Limited (NEFT credit on day 1–3 of month) ────────────
    (
        "Salary", "Salary",
        lambda p, dr, cr: bool(re.search(r"MPHASIS", p, re.IGNORECASE)) and cr > 0,
        0.97,
    ),

    # ── Salary / Payroll — generic ────────────────────────────────────
    (
        "Salary", "Salary",
        lambda p, dr, cr: bool(re.search(
            # \bSALARY\b fails on SALARYAPR2025 (no word-boundary before the month suffix)
            # so we match SALARY at a word boundary OR when followed by a letter (month abbrev)
            r"SALARY(?:\b|(?=[A-Z]))|SALARYTRANS|PAYROLL|PAYSLIP",
            p, re.IGNORECASE)) and cr > 0,
        0.95,
    ),

    # ── Bank Interest ─────────────────────────────────────────────────────
    (
        "Bank Interest", "Bank Interest",
        lambda p, dr, cr: bool(re.search(
            r"Int\.Pd[:.]|INTEREST\s*PAID|INT\s*PD\b|SB\s*INT:|SBINT:|INTEREST\s*CAPITALISED",
            p, re.IGNORECASE)) and cr > 0,
        0.95,
    ),

    # ── SIP — generic ACH / ECS / NACH debit ─────────────────────────────
    (
        "SIP", "SIP",
        lambda p, dr, cr: bool(re.search(
            r"\bNACH[- ]MUT[- ]DR\b|ACH\s*D[- ]+TP\s*ACH|INDIANESIGN|"
            r"BILLDKINDIAN|NACHINDIANCLEARING|ECS\s*D[- ]",
            p, re.IGNORECASE)) and dr > 0,
        0.90,
    ),

    # ── Dividend Income — ACH / ECS credit ───────────────────────────────
    (
        "Dividend Income", "Dividend Income",
        lambda p, dr, cr: bool(re.search(
            r"^ACH\s*C[- ]|^NACH[- ]ECS[- ]CR|^NACH[- ]10[- ]CR[- ]",
            p, re.IGNORECASE)) and cr > 0,
        0.90,
    ),

    # ── Dividend Income — DIV keyword ─────────────────────────────────────
    (
        "Dividend Income", "Dividend Income",
        lambda p, dr, cr: bool(re.search(
            r"\bDIV\d*\b|\bDIVIDEND\b",
            p, re.IGNORECASE)) and cr > 0,
        0.85,
    ),

    # ── Advance Tax / Income Tax payments ────────────────────────────────
    (
        "Advance Tax", "Advance Tax",
        lambda p, dr, cr: bool(re.search(
            r"ETAX|ADVANCE\s*TAX|TAX\s*PAY(?:MENT)?|NSDL\s*TDS\b|CBDT",
            p, re.IGNORECASE)) and dr > 0,
        0.92,
    ),

    # ── Income Tax Refund ─────────────────────────────────────────────────
    (
        "Income Tax Refund", "Income Tax",
        lambda p, dr, cr: bool(re.search(
            r"\bITDTAX\b\s*REFUND\b|\bITD\b\s*TAX\s*REFUND|\bIT\b\s*REFUND|\bTAX\s*REFUND\b|\bINCOME\s*TAX\s*REFUND\b",
            p, re.IGNORECASE)) and cr > 0,
        0.95,
    ),

    # ── Family Transfers ─────────────────────────────────────────────────
    (
        "Transfer - Sunita Gupta", "Sunita Gupta",
        lambda p, dr, cr: bool(re.search(r"SUNITA\s*GUPT(A)?|SUNITA\b|0094\b|60094\b", p, re.IGNORECASE)),
        0.88,
    ),
    (
        "Transfer - Ajay Gupta", "Ajay Gupta",
        lambda p, dr, cr: bool(re.search(
            r"AJAY\s*KUMAR\s*GUPT(A)?|AJAY\s*GUPT(A)?|\bAKG\b|5930\b|85930\b", p, re.IGNORECASE)),
        0.88,
    ),
    (
        "Transfer - Archit Gupta", "Archit Gupta",
        lambda p, dr, cr: bool(re.search(r"ARCHIT\s*GUPT(A)?|ARCHIT\b", p, re.IGNORECASE)),
        0.85,
    ),
    (
        "Transfer - Megha Gupta", "Megha Gupta",
        lambda p, dr, cr: bool(re.search(r"MEGHA\s*GUPT?A?|MEGHA\b|meghaghati|\bMiss\.?\s*MEG[H]?\b|\bMiss\.?\s*ME\b", p, re.IGNORECASE)),
        0.85,
    ),
    (
        "Transfer - Ajay Gupta HUF", "Ajay Gupta HUF",
        lambda p, dr, cr: bool(re.search(r"\bHUF\b|\bH\.U\.F\.\b", p, re.IGNORECASE)),
        0.88,
    ),

    # ── Mohith Reddy — Rent / Deposit / Deposit Return ────────────────────
    (
        "Rent", "Rent",
        lambda p, dr, cr: bool(re.search(r"MOHITH\s*(S\s*)?REDDY", p, re.IGNORECASE)) and dr == 23000,
        0.92,
    ),
    (
        "Security Deposit", "Security Deposit",
        lambda p, dr, cr: bool(re.search(r"MOHITH\s*(S\s*)?REDDY", p, re.IGNORECASE)) and dr > 0 and dr != 23000,
        0.90,
    ),
    (
        "Security Deposit Return", "Security Deposit",
        lambda p, dr, cr: bool(re.search(r"MOHITH\s*(S\s*)?REDDY", p, re.IGNORECASE)) and cr > 0,
        0.90,
    ),

    # ── Rent via CRED (exact amount, no RENT keyword in particulars) ─────
    # Handles cases like Kotak "payment on CRED" where the particulars don't
    # explicitly say RENT but the amount matches the known rent (₹23,000).
    # Placed after Mohith Reddy rules so direct-to-landlord UPI always wins.
    (
        "Rent Payment (via CRED)", "Rent",
        lambda p, dr, cr: bool(re.search(r"\bCRED\b", p, re.IGNORECASE)) and dr == 23000,
        0.88,
    ),

    # ── Cash Withdrawal ──────────────────────────────────────────────────
    (
        "Cash Withdrawal", "Cash",
        lambda p, dr, cr: bool(re.search(
            r"ATW[-/]|ATM\s*CASH|CWDR|CASH\s*WITHD|^ATL/|^ATW/",
            p, re.IGNORECASE)) and dr > 0,
        0.92,
    ),

    # ── Cash Deposit ─────────────────────────────────────────────────────
    (
        "Cash Deposit", "Cash",
        lambda p, dr, cr: bool(re.search(
            r"CASH\s*DEP(?:OSIT)?|CDM[-/]",
            p, re.IGNORECASE)) and cr > 0,
        0.92,
    ),

    # ── MF Redemption — generic AMC names ────────────────────────────────
    (
        "MF Redemption", "Mutual Funds",
        lambda p, dr, cr: bool(re.search(
            r"INVESCO|PPFAS|PARAG\s*PARIKH|MIRAE\s*ASSET|NIPPON|QUANT\s*SMALL|"
            r"AXIS\s*MF|HDFC\s*MF|SBI\s*MF|CAMS|KFIN|REDEMPTION|MF\s*REDEEM|BIRLA|BSLMF|ADITYA\s*BSLMF",
            p, re.IGNORECASE)) and cr > 0,
        0.85,
    ),

    # ── Upwork Income ────────────────────────────────────────────────────
    (
        "Upwork Income", "Misc Income",
        lambda p, dr, cr: bool(re.search(r"UPWORK", p, re.IGNORECASE)) and cr > 0,
        0.95,
    ),

    # ── UPI Reversal ─────────────────────────────────────────────────────
    (
        "UPI Reversal", "Personal",
        lambda p, dr, cr: bool(re.search(r"^REV[-/]UPI|UPI_CRADJ", p, re.IGNORECASE)),
        0.88,
    ),

    # ── Freelance Income — Payment Escrow (NEFT credit) ──────────────────
    # Freelance work received via payment escrow services
    # Matches 'PAYMENT ESCROW' (IndusInd escrow), bare 'ESCROW', etc.
    (
        "Freelance Income", "Misc Income",
        lambda p, dr, cr: bool(re.search(r"ESCROW", p, re.IGNORECASE)) and cr > 0,
        0.92,
    ),

    # ── Cashback & Rewards — NPCI BHIM ────────────────────────────────────
    # Cashback rewards from BHIM app like SuperMoney, Kiwi
    (
        "Cashback - BHIM", "Misc Income",
        lambda p, dr, cr: bool(re.search(r"NPCI\s*BHIM|bhimcashba", p, re.IGNORECASE)) and cr > 0,
        0.88,
    ),

    # ── Cashback & Rewards — Kiwi Tech ────────────────────────────────────
    (
        "Cashback - Kiwi", "Misc Income",
        lambda p, dr, cr: bool(re.search(r"GoKiwi|Kiwi\s*Tech|KIWI", p, re.IGNORECASE)) and cr > 0,
        0.88,
    ),

    # ── Cashback & Rewards — SuperMoney ───────────────────────────────────
    (
        "SuperMoney (Rewards)", "Misc Income",
        lambda p, dr, cr: bool(re.search(r"supermoney|SUPERMONEY", p, re.IGNORECASE)) and cr > 0,
        0.88,
    ),

    # ── Mutual Fund Redemption — Navi ────────────────────────────────────
    (
        "MF Redemption", "Mutual Funds",
        lambda p, dr, cr: bool(re.search(r"NAVI\s*MUTUA", p, re.IGNORECASE)) and cr > 0,
        0.88,
    ),

    # ── IRCTC Refund — Railway ticket refund ──────────────────────────────
    # Must match before generic refund rule
    (
        "UPI - IRCTC", "Travel",
        lambda p, dr, cr: bool(re.search(r"IRCTC", p, re.IGNORECASE)) and bool(re.search(r"REFUND|REVERSAL|REFU", p, re.IGNORECASE)) and cr > 0,
        0.92,
    ),

    # ── Travel / IRCTC Booking ───────────────────────────────────────────
    (
        "UPI - IRCTC", "Travel",
        lambda p, dr, cr: bool(re.search(r"IRCTC", p, re.IGNORECASE)) and dr > 0,
        0.88,
    ),

    # ── Travel / MakeMyTrip Booking ────────────────────────────────────────
    (
        "UPI - MakeMyTrip", "Travel",
        lambda p, dr, cr: bool(re.search(r"MAKEMYTRIP", p, re.IGNORECASE)) and dr > 0,
        0.88,
    ),

    # ── Wakefit Refund ───────────────────────────────────────────────────
    # Refund from wakefit or transfers from Archita Gupta (who bought on her behalf)
    (
        "Refund - Wakefit", "Shopping",
        lambda p, dr, cr: bool(re.search(r"wakefit|WAKEFIT", p, re.IGNORECASE)) and cr > 0,
        0.90,
    ),

    # ── Autope (mostly IRCTC train tickets) ──────────────────────────────
    (
        "UPI - IRCTC", "Travel",
        lambda p, dr, cr: bool(re.search(r"AUTOPE", p, re.IGNORECASE)),
        0.88,
    ),

    # ── Generic Self Transfers (Contra) ──────────────────────────────────
    (
        "Contra - SBI", "SBI 1227",
        lambda p, dr, cr: (
            bool(re.search(r"\bAAYUSH\b", p, re.IGNORECASE))
            and bool(re.search(r"STATE\s*BANK\s*OF\s*INDIA|SBI\b|SBIN", p, re.IGNORECASE))
        ),
        0.90,
    ),
    (
        "Contra - Kotak", "KOTAK 0333",
        lambda p, dr, cr: (
            bool(re.search(r"\bAAYUSH\b", p, re.IGNORECASE))
            and bool(re.search(r"KOTAK\b|KKBK", p, re.IGNORECASE))
        ),
        0.90,
    ),
    (
        "Contra - Jupiter", "FEDERAL 0847",
        lambda p, dr, cr: (
            bool(re.search(r"\bAAYUSH\b", p, re.IGNORECASE))
            and bool(re.search(r"JUPITER|FEDERAL\b|FDRL", p, re.IGNORECASE))
        ),
        0.90,
    ),
    (
        "Contra - Axis", "Axis",
        lambda p, dr, cr: (
            bool(re.search(r"\bAAYUSH\b", p, re.IGNORECASE))
            and bool(re.search(r"AXIS\b|UTIB", p, re.IGNORECASE))
        ),
        0.90,
    ),
    (
        "Contra - HDFC", "HDFC 5413",
        lambda p, dr, cr: (
            bool(re.search(r"\bAAYUSH\b", p, re.IGNORECASE))
            and bool(re.search(r"HDFC", p, re.IGNORECASE))
            and not bool(re.search(r"HDFC\s*SECURITIES|HDBFSS|HDFCLIFE|HDFC\s*MF|HDFC\s*MUTUAL\s*FUND|HDFCMF", p, re.IGNORECASE))
        ),
        0.90,
    ),
    (
        "Contra - SBM", "SBM",
        lambda p, dr, cr: (
            bool(re.search(r"\bAAYUSH\b", p, re.IGNORECASE))
            and bool(re.search(r"SBM\b|STCB", p, re.IGNORECASE))
        ),
        0.90,
    ),
    (
        "Contra - Self", "Transfer",
        lambda p, dr, cr: bool(re.search(r"\bAAYUSH\b", p, re.IGNORECASE)),
        0.80,
    ),

    # ── NEFT / RTGS / IMPS transfer ──────────────────────────────────────
    (
        "NEFT Transfer", "Transfer",
        lambda p, dr, cr: bool(re.search(
            r"\bNEFT\b|\bRTGS\b|\bIMPS\b|\bMMT\b|\bINFT\b",
            p, re.IGNORECASE)),
        0.70,
    ),

    # ── Mobile Banking Transfer ───────────────────────────────────────────
    (
        "MOB Transfer", "Transfer",
        lambda p, dr, cr: bool(re.search(
            r"\bMOB/TPFT\b|\bMOB/TFR\b|\bMOB\s*TFR\b",
            p, re.IGNORECASE)),
        0.70,
    ),

    # ── Internet Banking transfer ─────────────────────────────────────────
    (
        "IB Transfer", "Transfer",
        lambda p, dr, cr: bool(re.search(r"^IB:\s*", p, re.IGNORECASE)),
        0.72,
    ),

    # ── Misc Income — refunds / cashbacks / reversals ─────────────────────
    (
        "Misc Income", "Misc Income",
        lambda p, dr, cr: bool(re.search(
            r"REFUND|REVERSAL|CASHBACK|CREDIT\s*ADJ|\bREV\b",
            p, re.IGNORECASE)) and cr > 0,
        0.70,
    ),




    # ── G Kanthamma — second landlord (Rent / Deposit) ────────────────────
    # Payments with 'security', 'balanc', 'January', 'Feb mo', 'Token' in the
    # reference hint segment → monthly rent or deposit lump sums.
    (
        "Rent", "Rent",
        lambda p, dr, cr: bool(re.search(r"KANTHAMMA", p, re.IGNORECASE))
            and bool(re.search(r"Januar|Feb mo|March|month|rent", p, re.IGNORECASE))
            and dr > 0,
        0.90,
    ),
    (
        "Security Deposit", "Security Deposit",
        lambda p, dr, cr: bool(re.search(r"KANTHAMMA", p, re.IGNORECASE))
            and bool(re.search(r"secur|balanc|Token|advance|deposit|sendin", p, re.IGNORECASE))
            and dr > 0,
        0.90,
    ),
    (
        "Security Deposit Return", "Security Deposit",
        lambda p, dr, cr: bool(re.search(r"KANTHAMMA", p, re.IGNORECASE)) and cr > 0,
        0.88,
    ),
    # Generic fallback for any Kanthamma payment not matched above
    (
        "Rent", "Rent",
        lambda p, dr, cr: bool(re.search(r"KANTHAMMA", p, re.IGNORECASE)) and dr > 0,
        0.82,
    ),

    # ── INDmoney — investment platform ───────────────────────────────────
    (
        "INDmoney Investment", "Investments",
        lambda p, dr, cr: bool(re.search(r"INDmoney|INDMoney", p, re.IGNORECASE)) and dr > 0,
        0.88,
    ),

    # ── IPO / FPO / Rights Issue via UPI Mandate (ASBA) ─────────────────
    # SEBI's UPI-ASBA mechanism uses 'UPIM/' prefix (UPI Mandate) exclusively
    # for IPO block requests. Pattern: UPIM/<CompanyName>/<MandateRef>
    # Works for any IPO — Groww (Billionbrains), Hyundai, etc.
    (
        "IPO Application (UPI)", "Investments",
        lambda p, dr, cr: bool(re.match(r"UPIM/", p.strip(), re.IGNORECASE)) and dr > 0,
        0.92,
    ),

    # ── Mutual Fund Investment via ICCL, BSE, NSE or Clearing Corporation ───
    (
        "MF Investment", "Investments",
        lambda p, dr, cr: bool(re.search(r"iccl|BSE\s*MF|NSE\s*MF|INDIAN\s*CLEARING\s*CORP", p, re.IGNORECASE)) and dr > 0,
        0.90,
    ),

    # ── Zerodha via SBI (VPA truncated by SBI export) ─────────────────────
    # SBI wraps long lines so 'zerodha' appears as 'Zerodha ' or 'zerodha.\n rz'
    (
        "Zerodha Broking", "Zerodha Broking Limited",
        lambda p, dr, cr: bool(re.search(r"zerodha|zerodhab", p, re.IGNORECASE)),
        0.88,
    ),

    # ── Care / Max / Niva Health Insurance ─────────────────────────────────
    (
        "Health Insurance", "Health Insurance",
        lambda p, dr, cr: bool(re.search(r"Care\s*Health\s*Insur|Max\s*Bupa|MaxBupa|Niva\s*Bupa|Religare|Star\s*Health|Bajaj\s*Allianz", p, re.IGNORECASE)) and dr > 0,
        0.92,
    ),

    # ── FASTag toll payments (NHAI annual pass only) ─────────────────────────────
    # Remove AUTOPE (user-specific payment solution, not toll)
    # Keep only FASTAG and NHAI annual pass
    (
        "Toll / FASTag", "Transport",
        lambda p, dr, cr: bool(re.search(r"FASTAG|FASTag|National\s*Highways\s*Aut(?:h)?", p, re.IGNORECASE)) and dr > 0,
        0.88,
    ),

    # ── DMart (Avenue Supermarts) ─────────────────────────────────────────
    (
        "UPI - DMart", "Groceries",
        lambda p, dr, cr: bool(re.search(r"AVENUE\s*SUPERMARTS|DMART", p, re.IGNORECASE)) and dr > 0,
        0.88,
    ),

    # ── Nandini (Karnataka dairy cooperative) ────────────────────────────
    # Small daily milk payments; 'Nandini' is the Karnataka milk brand VPA name.
    (
        "UPI - Nandini Dairy", "Groceries",
        lambda p, dr, cr: bool(re.search(r"\bNandini\b", p, re.IGNORECASE))
            and dr > 0 and dr <= 500,
        0.82,
    ),

    # ── District app — restaurant / dining ───────────────────────────────
    (
        "UPI - District (Dining)", "Food & Dining",
        lambda p, dr, cr: bool(re.search(r"District\s*Dining|DISTRICT\s*D\b|DistrictDining", p, re.IGNORECASE)) and dr > 0,
        0.85,
    ),

    # ── Fruit / vegetable vendors (VPA domain keyword) ───────────────────
    (
        "UPI - Fresh Produce", "Groceries",
        lambda p, dr, cr: bool(re.search(r"fruits|FRUIT\s*JU|FRUIT\b|vegetab|VEGET", p, re.IGNORECASE)) and dr > 0,
        0.82,
    ),

    # ── Bannerghatta Biological Park ─────────────────────────────────────
    (
        "Entertainment", "Entertainment",
        lambda p, dr, cr: bool(re.search(r"BANNERGHATTA|Biological\s*Park", p, re.IGNORECASE)) and dr > 0,
        0.88,
    ),

    # ── Google Play / OpenAI / SaaS subscriptions ────────────────────────
    (
        "UPI - Google Play", "Subscriptions",
        lambda p, dr, cr: bool(re.search(r"Google\s*Play", p, re.IGNORECASE)) and dr > 0,
        0.88,
    ),
    (
        "UPI - OpenAI", "Subscriptions",
        lambda p, dr, cr: bool(re.search(r"OpenAI", p, re.IGNORECASE)),
        0.88,
    ),

    # ── Lounge Access Charge — Dreamfolks ─────────────────────────────────
    # Travel lounge access charges
    (
        "Lounge Access Charge", "Bank Charges",
        lambda p, dr, cr: bool(re.search(r"DREAMFOLKS|TRAVEL\s*CLUB\s*LOUN|LOUNGE\s*ACCESS", p, re.IGNORECASE)) and dr > 0,
        0.85,
    ),

    # ── SBIMOPS — SBI Merchant Online Payment System (govt/utility) ───────
    (
        "Govt / Utility Payment", "Utilities",
        lambda p, dr, cr: bool(re.search(r"SBIMOPS|MOPSUPITxn", p, re.IGNORECASE)) and dr > 0,
        0.82,
    ),

    # ── Yash Gupta — dining/event reimbursement ───────────────────────────
    # Paid on behalf; treated as personal spend (not family transfer).
    (
        "UPI Payment", "Personal",
        lambda p, dr, cr: bool(re.search(r"YASH\s*GUPTA", p, re.IGNORECASE)) and dr > 0,
        0.75,
    ),

    # ── ABHINDAN — own shop transfer (Contra - Self) ──────────────────────
    # ₹39,674 transferred to own business; Ajay returned ~40K separately.
    (
        "Contra - Self", "Transfer",
        lambda p, dr, cr: bool(re.search(r"ABHINDAN", p, re.IGNORECASE)) and dr > 0,
        0.80,
    ),

    # ── Vehicle service shops — fuel stations and service centers ───────────────────
    # BENAKA ENTERPRISES, TWO LAXMI PATIL, KAMADENU are vehicle-related services
    (
        "Vehicle Service", "Transport",
        lambda p, dr, cr: bool(re.search(
            r"BENAKA\s*ENTERP|TWO\s*LAXMI\s*PATIL|KAMADENU\s*SERVICE",
            p, re.IGNORECASE)) and dr > 0,
        0.82,
    ),

    # ── Dining / Hotel (KAKE DI HATTI only) ────────────────────────────────────────
    # Removed Sri Vinayaka Hotel and Hotel Top In Town (miscategorized)
    (
        "Food & Dining / Hotel", "Food & Dining",
        lambda p, dr, cr: bool(re.search(r"KAKE\s*DI\s*HATTI", p, re.IGNORECASE)) and dr > 0,
        0.82,
    ),

    # ── KEERTHANA MOTORS — vehicle service / repair ───────────────────────
    (
        "Vehicle Service", "Transport",
        lambda p, dr, cr: bool(re.search(r"KEERTHANA\s*MOTORS", p, re.IGNORECASE)) and dr > 0,
        0.85,
    ),

    # ── GET WELL SOON PHARMACY — healthcare ───────────────────────────────
    (
        "UPI - Pharmacy", "Healthcare",
        lambda p, dr, cr: bool(re.search(r"GET\s*WELL\s*SOON|PHARMAC", p, re.IGNORECASE)) and dr > 0,
        0.85,
    ),

    # ── Airtel WiFi payments via CRED / CRED Wallet ────────────────────────
    (
        "Airtel WiFi", "Utilities",
        lambda p, dr, cr: (
            bool(re.search(r"CRED", p, re.IGNORECASE))
            and (
                abs(dr - 686.82) < 0.01 or
                abs(dr - 412.42) < 0.01 or
                abs(dr - 410.26) < 0.01 or
                abs(dr - 265.06) < 0.01 or
                abs(dr - 330.06) < 0.01 or
                abs(dr - 414.26) < 0.01
            )
        ),
        0.95,
    ),

    # ── D P ABHUSHAN — jewellery shop ─────────────────────────────────────
    (
        "Shopping - Jewellery", "Shopping",
        lambda p, dr, cr: bool(re.search(r"ABHUSHAN", p, re.IGNORECASE)) and dr > 0,
        0.85,
    ),

    # ── SuperMoney Contra to Kotak (KKBK) ──────────────────────────────────
    (
        "Contra - Kotak", "KOTAK 0333",
        lambda p, dr, cr: bool(re.search(r"95944352", p)) and bool(re.search(r"KKBK|KOTAK", p, re.IGNORECASE)),
        0.88,
    ),

    # ── SuperMoney Contra to SBI (SBIN) ────────────────────────────────────
    (
        "Contra - SBI", "SBI 1227",
        lambda p, dr, cr: bool(re.search(r"95944352", p)) and bool(re.search(r"SBIN|STATE\s*BANK|SBI\b", p, re.IGNORECASE)),
        0.88,
    ),

    # ── SuperMoney Contra to Jupiter (FDRL) ────────────────────────────────
    (
        "Contra - Jupiter", "FEDERAL 0847",
        lambda p, dr, cr: bool(re.search(r"95944352", p)) and bool(re.search(r"FDRL|FEDERAL|JUPITER", p, re.IGNORECASE)),
        0.88,
    ),

    # ── SuperMoney Contra to Axis (UTIB) ───────────────────────────────────
    (
        "Contra - Axis", "Axis",
        lambda p, dr, cr: bool(re.search(r"95944352", p)) and bool(re.search(r"UTIB|AXIS", p, re.IGNORECASE)),
        0.88,
    ),

    # ── SuperMoney Contra to HDFC ──────────────────────────────────────────
    (
        "Contra - HDFC", "HDFC 5413",
        lambda p, dr, cr: bool(re.search(r"95944352", p)) and bool(re.search(r"HDFC", p, re.IGNORECASE)),
        0.88,
    ),

    # ── SuperMoney Contra to SBM (STCB) ────────────────────────────────────
    (
        "Contra - SBM", "SBM",
        lambda p, dr, cr: bool(re.search(r"95944352", p)) and bool(re.search(r"STCB|SBM\b", p, re.IGNORECASE)),
        0.88,
    ),

    # ── SuperMoney Contra Fallback (no bank inferred) ─────────────────────
    (
        "Contra - Self (SuperMoney)", "Personal",
        lambda p, dr, cr: bool(re.search(r"95944352", p)),
        0.82,
    ),

    # ── Generic UPI Payment (debit) — merchant detection happens in classifier
    (
        "UPI Payment", "Personal",
        lambda p, dr, cr: bool(re.search(r"\bUPI[/ -]|UPIOUT/", p, re.IGNORECASE)) and dr > 0,
        0.55,
    ),

    # ── Generic UPI Receipt (credit) ─────────────────────────────────────
    (
        "UPI Receipt", "Personal",
        lambda p, dr, cr: bool(re.search(r"\bUPI[/ -]|UPIIN/", p, re.IGNORECASE)) and cr > 0,
        0.55,
    ),

    # ── Fallback ──────────────────────────────────────────────────────────
    (
        "What is this?", "Suspense",
        lambda p, dr, cr: True,
        0.0,
    ),
]
