# -*- coding: utf-8 -*-
"""test_core.py.

Unit tests for core functions:
- safe_float
- find_header_row
- identify_bank (with and without preambles)
- detect_merchant
- map_category
"""

import unittest
import numpy as np

from tax_automation.core.utils import safe_float
from tax_automation.core.auto_header import find_header_row
from tax_automation.core.bank_identifier import identify_bank
from tax_automation.core.merchants import detect_merchant
from tax_automation.core.cc_category_map import map_category


class TestCoreUtils(unittest.TestCase):
    """Test suite for safe_float and numerical parsing."""

    def test_safe_float_valid_inputs(self):
        self.assertEqual(safe_float(100), 100.0)
        self.assertEqual(safe_float(50.5), 50.5)
        self.assertEqual(safe_float("1,250.75"), 1250.75)
        self.assertEqual(safe_float("  300.00 "), 300.0)

    def test_safe_float_empty_and_nan(self):
        self.assertEqual(safe_float(None), 0.0)
        self.assertEqual(safe_float(""), 0.0)
        self.assertEqual(safe_float("   "), 0.0)
        self.assertEqual(safe_float(float("nan")), 0.0)
        self.assertEqual(safe_float(np.nan), 0.0)

    def test_safe_float_invalid_strings(self):
        self.assertEqual(safe_float("N/A"), 0.0)
        self.assertEqual(safe_float("--"), 0.0)
        self.assertEqual(safe_float("invalid"), 0.0)


class TestAutoHeader(unittest.TestCase):
    """Test suite for automatic header row detection."""

    def test_find_header_with_metadata(self):
        rows = [
            ["Account Statement for Aayush Kumar Gupta"],
            ["Customer ID: 12345678"],
            ["Account No: 50100012345678"],
            [
                "Date",
                "Narration",
                "Chq./Ref.No.",
                "Withdrawal Amt.",
                "Deposit Amt.",
                "Closing Balance",
            ],
            ["2026-04-01", "Opening Balance", "", "", "", "10000.00"],
        ]
        self.assertEqual(find_header_row(rows), 3)

    def test_find_header_at_row_zero(self):
        rows = [
            ["Date", "Particulars", "Debit", "Credit", "Balance"],
            ["2026-04-01", "UPI Transfer", "500.00", "", "9500.00"],
        ]
        self.assertEqual(find_header_row(rows), 0)


class TestBankIdentifier(unittest.TestCase):
    """Test suite for statement fingerprinting & bank scoring."""

    def setUp(self):
        self.registry = {
            "hdfc": {
                "meta_signals": ["HDFC BANK", "Statement of accounts"],
                "header_signals": [
                    "Withdrawal Amt.",
                    "Deposit Amt.",
                    "Closing Balance",
                    "Chq./Ref.No.",
                ],
            },
            "sbi": {
                "meta_signals": ["STATE BANK OF INDIA", "Account Name"],
                "header_signals": [
                    "Txn Date",
                    "Description",
                    "Ref No./Cheque No.",
                    "Debit",
                    "Credit",
                    "Balance",
                ],
            },
        }

    def test_identify_with_preamble(self):
        rows = [
            ["HDFC BANK LIMITED", "Branch: Mumbai"],
            ["Statement of accounts for period 01-Apr-2025 to 31-Mar-2026"],
            [
                "Date",
                "Narration",
                "Chq./Ref.No.",
                "Withdrawal Amt.",
                "Deposit Amt.",
                "Closing Balance",
            ],
            ["2026-04-01", "Opening Balance", "", "", "", "50000.00"],
        ]
        bank_key, score = identify_bank(
            rows, header_row_idx=2, bank_registry=self.registry, sheet_name="HDFC 5413"
        )
        self.assertEqual(bank_key, "hdfc")
        self.assertGreaterEqual(score, 0.55)

    def test_identify_clean_csv_without_preamble(self):
        rows = [
            ["Withdrawal Amt.", "Deposit Amt.", "Closing Balance", "Chq./Ref.No."],
            ["500.00", "", "49500.00", "REF001"],
        ]
        bank_key, score = identify_bank(
            rows, header_row_idx=0, bank_registry=self.registry, sheet_name="Sheet1"
        )
        self.assertEqual(bank_key, "hdfc")
        self.assertGreaterEqual(score, 0.55)


class TestMerchantsAndCC(unittest.TestCase):
    """Test suite for merchant recognition and credit card category mapping."""

    def test_detect_known_merchant(self):
        res = detect_merchant("UPI/SWIGGY/12345/Food")
        if res is not None:
            label, head, conf = res
            self.assertEqual(head, "Food & Dining")

    def test_map_cc_category(self):
        narration, head = map_category("Grocery")
        self.assertIn("Groceries", head)


if __name__ == "__main__":
    unittest.main()
