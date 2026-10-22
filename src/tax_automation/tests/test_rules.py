# -*- coding: utf-8 -*-
"""test_rules.py.

Unit tests for dynamic rule compiler and rule generation:
- Contra synthesis (inter-account and self-transfers)
- Rent rule synthesis
- Family member rules
- Declarative custom rules compilation (exact amounts, directional filters)
"""

import unittest

from tax_automation.rules.loader import (
    build_dynamic_contra_rules,
    build_dynamic_rent_rules,
    build_dynamic_family_rules,
    build_dynamic_custom_rules,
    build_rule_chain,
)


class TestRulesEngine(unittest.TestCase):
    """Test suite for dynamic rule compiler and synthesis."""

    def setUp(self):
        self.entity_config = {
            "entity_id": "test_person",
            "display_name": "Test Person",
            "self_patterns": [r"\bTEST\s*PERSON\b"],
            "self_vpas": ["testperson@upi"],
            "accounts": [
                {
                    "account_key": "hdfc",
                    "bank": "hdfc",
                    "account_id": "HDFC 5413",
                    "display_name": "HDFC Bank",
                },
                {
                    "account_key": "kotak",
                    "bank": "kotak",
                    "account_id": "KOTAK 0333",
                    "display_name": "Kotak Bank",
                },
            ],
            "family_members": [
                {
                    "name": "Spouse Person",
                    "relationship": "Spouse",
                    "account_head": "Spouse Person",
                    "patterns": [r"\bSPOUSE\b"],
                }
            ],
            "rent": {
                "landlords": ["LANDLORD NAME"],
                "vpas": ["landlord@upi"],
                "keywords": ["RENT"],
            },
            "custom_rules": [
                {
                    "label": "Custom SIP",
                    "account_head": "Investments",
                    "pattern": "ZERODHA",
                    "direction": "DR",
                    "exact_amount": 5000.0,
                    "confidence": 0.99,
                    "layer": "entity",
                }
            ],
        }

    def test_contra_rules_synthesis(self):
        contra_rules = build_dynamic_contra_rules(self.entity_config, "hdfc")
        self.assertTrue(len(contra_rules) >= 2)

        # First rule should target Kotak Bank account
        label, head, match_fn, conf = contra_rules[0]
        self.assertIn("Kotak", label)
        self.assertEqual(head, "KOTAK 0333")

        # Test matching Kotak transfer to self
        self.assertTrue(match_fn("UPI/TEST PERSON/KOTAK/123", 5000.0, 0.0))
        # Non-self transfer shouldn't match
        self.assertFalse(match_fn("UPI/OTHER PERSON/KOTAK/123", 5000.0, 0.0))

        # Check general self-transfer rule
        generic_rule = contra_rules[-1]
        self.assertEqual(generic_rule[0], "Contra - Self Transfer")
        self.assertTrue(generic_rule[2]("Self transfer to savings", 1000.0, 0.0))

    def test_rent_rules_synthesis(self):
        rent_rules = build_dynamic_rent_rules(self.entity_config)
        self.assertEqual(len(rent_rules), 1)
        label, head, match_fn, conf = rent_rules[0]

        # Valid rent payments (Debit > 0 and contains rent token)
        self.assertTrue(match_fn("UPI/LANDLORD NAME/Flat 101", 25000.0, 0.0))
        self.assertTrue(match_fn("MONTHLY RENT APRIL", 25000.0, 0.0))
        # Word boundary protection: PARENT should not match RENT
        self.assertFalse(match_fn("TRANSFER TO PARENTS", 25000.0, 0.0))
        # Rent received (Credit) should not match debit rent rule
        self.assertFalse(match_fn("MONTHLY RENT", 0.0, 25000.0))

    def test_family_rules_synthesis(self):
        family_rules = build_dynamic_family_rules(self.entity_config)
        self.assertEqual(len(family_rules), 1)
        label, head, match_fn, conf = family_rules[0]
        self.assertEqual(label, "Transfer - Spouse Person")
        self.assertEqual(head, "Spouse Person")
        self.assertTrue(match_fn("UPI/SPOUSE/GIFT", 500.0, 0.0))
        self.assertFalse(match_fn("UPI/OTHER/GIFT", 500.0, 0.0))

    def test_custom_rule_compilation(self):
        rules = build_dynamic_custom_rules(self.entity_config, layer="entity")
        self.assertEqual(len(rules), 1)
        label, head, match_fn, conf = rules[0]
        self.assertEqual(label, "Custom SIP")

        # Exact amount 5000 DR matches
        self.assertTrue(match_fn("ZERODHA BROKING", 5000.0, 0.0))
        # Different amount fails
        self.assertFalse(match_fn("ZERODHA BROKING", 5001.0, 0.0))
        # Credit direction fails
        self.assertFalse(match_fn("ZERODHA BROKING", 0.0, 5000.0))

    def test_build_rule_chain(self):
        bank_rules, common_rules = build_rule_chain("aayush", "hdfc")
        self.assertIsInstance(bank_rules, list)
        self.assertIsInstance(common_rules, list)
        self.assertTrue(len(bank_rules) > 0)
        self.assertTrue(len(common_rules) > 0)


if __name__ == "__main__":
    unittest.main()
