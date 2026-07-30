# -*- coding: utf-8 -*-
"""
bank_registry.py
================
Central registry of all supported banks for Ajay Gupta.

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
# Self-transfer UPI reference numbers (FY25/FY26).
# Update this list each FY if new self-transfer refs are found.
# ---------------------------------------------------------------------------
SELF_UPI_REFS = [
    # Add any known UPI reference numbers for Ajay's self transfers here if needed
]

# ---------------------------------------------------------------------------
# BANK_REGISTRY
# ---------------------------------------------------------------------------
BANK_REGISTRY: dict[str, dict] = {

    # ── HDFC Bank ──────────────────────────────────────────────────────────
    "hdfc": {
        "display_name"  : "HDFC Bank",
        "account_id"    : "HDFC 5930",
        "sheet_name"    : "HDFC 5930",
        "meta_signals"  : [
            "HDFC",
            "5930",
            "HDFC BANK",
            "Withdrawal Amt",
            "Closing Balance",
            "Statement of accounts",
        ],
        "header_signals": [
            "Withdrawal Amt.",
            "Deposit Amt.",
            "Closing Balance",
        ],
        "col_date"        : "Date",
        "col_particulars" : "Narration",
        "col_narration_h" : "Narration",
        "col_dr"          : "Withdrawal Amt.",
        "col_cr"          : "Deposit Amt.",
        "col_balance"     : "Closing Balance",
        "col_ref"         : "Chq./Ref.No.",
        "col_value_date"  : "Value Dt",
        "rules_module"    : "narration_engine.rules_hdfc",
    },

    # ── Axis Bank ──────────────────────────────────────────────────────────
    "axis": {
        "display_name"  : "Axis Bank",
        "account_id"    : "AXIS 3167",
        "sheet_name"    : "AXIS 3167",
        "meta_signals"  : [
            "UTIB",
            "AXIS",
            "PARTICULARS",
            "3167",
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

    # ── Bank of India ──────────────────────────────────────────────────────
    "boi": {
        "display_name"  : "Bank of India",
        "account_id"    : "BOI 6699",
        "sheet_name"    : "BOI 6699",
        "meta_signals"  : [
            "BKID",
            "662113100016699",
            "BOI",
            "6699",
            "Bank of India",
        ],
        "header_signals": [
            "Debit",
            "Credit",
            "Cr/Dr",
            "Amount(INR)",
        ],
        "col_date"        : ["Date", "Txn Date"],
        "col_particulars" : ["Remarks", "Description"],
        "col_narration_h" : "Narration",
        "col_dr"          : "Debit",
        "col_cr"          : "Credit",
        "col_balance"     : ["Balance Amount", "Balance(INR)", "Balance"],
        "col_ref"         : ["Cheque No.", "Ref No./Cheque No.", "Ref No/Cheque No"],
        "col_value_date"  : None,
        "rules_module"    : "narration_engine.rules_boi",
    },

    # ── SBI Current Account ────────────────────────────────────────────────
    "sbi_ca": {
        "display_name"  : "SBI Current Account",
        "account_id"    : "SBI Current Account",
        "sheet_name"    : "SBI CA",
        "meta_signals"  : [
            "State Bank of India",
            "Current Account",
            "Drawing Power",
            "Account Number",
        ],
        "header_signals": [
            "Txn Date",
            "Description",
            "Debit",
            "Credit",
            "Balance",
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

    # ── SBI Overdraft Account ──────────────────────────────────────────────
    "sbi_od": {
        "display_name"  : "SBI OD 5441",
        "account_id"    : "SBI OD 5441",
        "sheet_name"    : "SBI OD 5441",
        "meta_signals"  : [
            "State Bank of India",
            "5441",
            "OD",
            "OVERDRAFT",
        ],
        "header_signals": [
            "Txn Date",
            "Description",
            "Debit",
            "Credit",
            "Balance",
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

    # ── SBI Saving Nashik ──────────────────────────────────────────────────
    "sbi_nsk": {
        "display_name"  : "SBI Saving Nashik",
        "account_id"    : "SBI SB Nsk",
        "sheet_name"    : "SBI SB Nsk",
        "meta_signals"  : [
            "State Bank of India",
            "Nashik",
            "Nsk",
        ],
        "header_signals": [
            "Txn Date",
            "Description",
            "Debit",
            "Credit",
            "Balance",
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

    # ── SBI Saving Kota ────────────────────────────────────────────────────
    "sbi_kota": {
        "display_name"  : "SBI Saving Kota",
        "account_id"    : "SBI SB Kota",
        "sheet_name"    : "SBI SB Kota",
        "meta_signals"  : [
            "State Bank of India",
            "Kota",
        ],
        "header_signals": [
            "Txn Date",
            "Description",
            "Debit",
            "Credit",
            "Balance",
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

    # ── SBI Saving Rawatbhata ──────────────────────────────────────────────
    "sbi_rawatbhata": {
        "display_name"  : "SBI Saving Rawatbhata",
        "account_id"    : "SBI SB Rawatbhata",
        "sheet_name"    : "SBI SB Rawatbhata",
        "meta_signals"  : [
            "State Bank of India",
            "rawatbhata",
        ],
        "header_signals": [
            "Txn Date",
            "Description",
            "Debit",
            "Credit",
            "Balance",
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

    # ── SBI Insurance Loan ─────────────────────────────────────────────────
    "sbi_ins_loan": {
        "display_name"  : "SBI Insurance Loan Nashik",
        "account_id"    : "SBI Insurance Loan",
        "sheet_name"    : "SBI Insurance Loan",
        "meta_signals"  : [
            "State Bank of India",
            "Insurance loan",
        ],
        "header_signals": [
            "Txn Date",
            "Description",
            "Debit",
            "Credit",
            "Balance",
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

    # ── SBI Flat Insurance Account ─────────────────────────────────────────
    "sbi_flat_ins": {
        "display_name"  : "SBI Flat Insurance Account",
        "account_id"    : "Ajay SBI Flat Insurance",
        "sheet_name"    : "SBI Flat Insurance Account",
        "meta_signals"  : [
            "Flat Insurance",
        ],
        "header_signals": [
            "Txn Date",
            "Description",
            "Debit",
            "Credit",
            "Balance",
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

    # ── SBI Bank 3479 ──────────────────────────────────────────────────────
    "sbi_bank_3479": {
        "display_name"  : "SBI Bank 3479",
        "account_id"    : "SBI Bank 3479",
        "sheet_name"    : "SBI Bank 3479",
        "meta_signals"  : [
            "3479",
        ],
        "header_signals": [
            "Txn Date",
            "Description",
            "Debit",
            "Credit",
            "Balance",
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

    # ── HUF Current Account ─────────────────────────────────────────────────
    "huf_ca": {
        "display_name"  : "Ajay HUF Current Account",
        "account_id"    : "HUF Current Account",
        "sheet_name"    : "HUF Current",
        "meta_signals"  : [
            "HUF",
            "OpTransactionHistory",
        ],
        "header_signals": [
            "Date",
            "Particulars",
            "Withdrawals",
            "Deposits",
            "Balance",
        ],
        "col_date"        : "Date",
        "col_particulars" : ["Remarks", "Particulars"],
        "col_narration_h" : "Narration",
        "col_dr"          : "Withdrawals",
        "col_cr"          : "Deposits",
        "col_balance"     : "Balance",
        "col_ref"         : "Tran ID",
        "col_value_date"  : "Value Date",
        "rules_module"    : "narration_engine.rules_huf",
    },
}

# Sheets that are outputs or calculation aids (not bank data) — always skipped during bank detection
OUTPUT_SHEET_NAMES = {
    "For Tally", "Conso", "Bank Summary", "Salary", "Leave Encashment", 
    "Contra Summary", "EquityRelated"
}
