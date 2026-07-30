# -*- coding: utf-8 -*-
"""
bank_registry.py
================
Central registry of all supported banks.

To add a new bank next year:
  1. Add one entry to BANK_REGISTRY with its fingerprint signals and column mappings.
  2. Create a matching rules_<bank_key>.py in this package.
  3. No other file needs to change.

Fingerprint scoring weights:
  meta_score   = fraction of meta_signals found in sheet metadata text
  header_score = fraction of header_signals found in the detected header row
  final_score  = 0.60 * meta_score + 0.40 * header_score
  Minimum threshold to be identified: 0.55
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Self-transfer UPI reference numbers (FY25).
# These appear in KOTAK Particulars as "UPI/AAYUSH KUMAR GU/<ref>/..."
# when Aayush transfers money to his own SBI or Jupiter accounts.
# Update this list each FY if new self-transfer refs are found.
# ---------------------------------------------------------------------------
SELF_UPI_REFS_JUPITER = [
    "409319949339", "409518581802", "409860235500", "410013514219",
    "410480092425", "410798005765", "413856144623", "413856342655",
    "413859249444",
]
SELF_UPI_REFS_SBI = [
    "409308961216", "412101194543", "416418674665", "416418731041",
]

# Known rent VPA / beneficiary for SBI (Nagaraj A - landlord)
RENT_VBAS_SBI = ["4897690162095"]


# ---------------------------------------------------------------------------
# BANK_REGISTRY
# ---------------------------------------------------------------------------
BANK_REGISTRY: dict[str, dict] = {

    # ── HDFC Bank ──────────────────────────────────────────────────────────
    "hdfc": {
        "display_name"  : "HDFC Bank",
        "account_id"    : "HDFC 5413",
        # Fingerprint signals — strings to look for in sheet metadata (rows before header)
        "meta_signals"  : [
            "HDFC BANK",
            "Withdrawal Amt",
            "Closing Balance",
            "Statement of accounts",
            "Account No :",
        ],
        # Signals in the actual header row column names
        "header_signals": [
            "Withdrawal Amt.",
            "Deposit Amt.",
            "Closing Balance",
            "Chq./Ref.No.",
        ],
        # Column name mappings (after header is located)
        "col_date"        : "Date",
        "col_particulars" : "Narration",        # HDFC calls it Narration
        "col_narration_h" : "Narration",        # human narration (pandas renames dup to .1)
        "col_dr"          : "Withdrawal Amt.",
        "col_cr"          : "Deposit Amt.",
        "col_balance"     : "Closing Balance",
        "col_ref"         : "Chq./Ref.No.",
        "col_value_date"  : "Value Dt",
        "rules_module"    : "narration_engine.rules_hdfc",
    },

    # ── Kotak Mahindra Bank ────────────────────────────────────────────────
    "kotak": {
        "display_name"  : "Kotak Mahindra Bank",
        "account_id"    : "KOTAK 0333",
        "meta_signals"  : [
            "Cust. Reln. No.",
            "Account Statement",
            "KKBK",
            "Account No.",
        ],
        "header_signals": [
            "Transaction Date",
            "Description",
            "Chq / Ref No.",
            "Dr / Cr",
        ],
        "col_date"        : "Transaction Date",
        "col_particulars" : "Description",
        "col_narration_h" : "Narration",
        "col_dr"          : "DR",
        "col_cr"          : "CR",
        "col_balance"     : "Balance",
        "col_ref"         : "Chq / Ref No.",
        "col_value_date"  : "Value Date",
        "rules_module"    : "narration_engine.rules_kotak",
    },

    # ── Axis Bank ──────────────────────────────────────────────────────────
    "axis": {
        "display_name"  : "Axis Bank",
        "account_id"    : "AXIS",
        "meta_signals"  : [
            "UTIB",
            "SRL NO",
            "PARTICULARS",
            "Statement of Account No",
        ],
        "header_signals": [
            "SRL NO",
            "PARTICULARS",
            "CHQNO",
            "Tran Date",
        ],
        "col_date"        : "Tran Date",
        "col_particulars" : "PARTICULARS",
        "col_narration_h" : "Narration",
        "col_dr"          : "DR",
        "col_cr"          : "CR",
        "col_balance"     : "BAL",
        "col_ref"         : "CHQNO",
        "col_value_date"  : None,
        "rules_module"    : "narration_engine.rules_axis",
    },

    # ── State Bank of India ────────────────────────────────────────────────
    "sbi": {
        "display_name"  : "State Bank of India",
        "account_id"    : "SBI 1227",
        "meta_signals"  : [
            "Drawing Power",
            "REGULAR SB CHQ",
            "Interest Rate",
            "Account Number",
            "SHIVAJI NAGAR",
        ],
        "header_signals": [
            "Txn Date",
            "Ref No./Cheque No.",
            "Debit",
            "Credit",
        ],
        "col_date"        : ["Txn Date", "Date"],
        "col_particulars" : ["Details", "Description"],
        "col_narration_h" : "Narration",
        "col_dr"          : "Debit",
        "col_cr"          : "Credit",
        "col_balance"     : "Balance",
        "col_ref"         : ["Ref No./Cheque No.", "Ref No/Cheque No"],
        "col_value_date"  : "Value Date",
        "rules_module"    : "narration_engine.rules_sbi",
    },

    # ── Federal Bank (Jupiter) ─────────────────────────────────────────────
    "federal": {
        "display_name"  : "Federal Bank (Jupiter)",
        "account_id"    : "FEDERAL 0847",
        "meta_signals"  : [
            "FDRL0007777",
            "77770101840847",
            "SALARY-7777",
            "Neo Banking",
            "Jupiter",
        ],
        "header_signals": [
            "Tran Type",
            "Tran ID",
            "Withdrawals",
            "Deposits",
        ],
        "col_date"        : "Date",
        "col_particulars" : "Particulars",
        "col_narration_h" : "Narration",
        "col_dr"          : "Withdrawals",
        "col_cr"          : "Deposits",
        "col_balance"     : "Balance",
        "col_ref"         : "Tran ID",
        "col_value_date"  : "Value Date",
        "rules_module"    : "narration_engine.rules_federal",
    },

    # ── SBM Bank ───────────────────────────────────────────────────────────
    "sbm": {
        "display_name"  : "SBM Bank",
        "account_id"    : "SBM",
        "meta_signals"  : [
            "STCB",
            "MICR Code : 110332002",
            "Savings Account  No.",
            "R003428697",
        ],
        "header_signals": [
            "Cheque Details",
            "Withdrawals",
            "Deposits",
        ],
        "col_date"        : "Date",
        "col_particulars" : "Particulars",
        "col_narration_h" : "Narration",
        "col_dr"          : "Withdrawals",
        "col_cr"          : "Deposits",
        "col_balance"     : "Balance",
        "col_ref"         : "Cheque Details",
        "col_value_date"  : None,
        "rules_module"    : "narration_engine.rules_sbm",
    },
}

# Sheets that are outputs (not bank data) — always skipped during bank detection
OUTPUT_SHEET_NAMES = {"For Tally", "Conso", "Bank Summary"}
