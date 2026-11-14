"""Generic identity precedence, without any production person names."""

import unittest

from tax_automation.core.person_identity import identity_matches
from tax_automation.rules.loader import (
    build_dynamic_family_rules,
    build_dynamic_contra_rules,
)


class TestPersonIdentity(unittest.TestCase):
    def setUp(self):
        self.ids = {
            "mira": {"names": ["Mira Shah"], "patterns": [r"\bMIRA\b"]},
            "arun": {"names": ["Arun Shah"], "patterns": [r"ARUN\s*SHAH"]},
        }

    def test_middle_name_containing_other_person_resolves_to_full_name(self):
        self.assertEqual(identity_matches("MRS. MIRA ARUN SHAH", self.ids), {"mira"})
        self.assertEqual(
            identity_matches(
                "MRS. MIRA ARUN SHAH", dict(reversed(list(self.ids.items())))
            ),
            {"mira"},
        )

    def test_distinct_counterparties_are_not_collapsed(self):
        self.assertEqual(
            identity_matches("MIRA SHAH TO ARUN SHAH", self.ids), {"mira", "arun"}
        )
        self.assertEqual(
            identity_matches("MIRA AND ARUN SHAH", self.ids), {"mira", "arun"}
        )

    def test_two_people_with_identical_alias_remain_ambiguous(self):
        self.ids["other_mira"] = {"names": ["Mira Shah"]}
        self.assertEqual(
            identity_matches("MIRA SHAH", self.ids), {"mira", "other_mira"}
        )

    def test_no_full_name_match_across_bank_delimiters(self):
        self.assertEqual(identity_matches("MIRA/ARUN SHAH", self.ids), {"mira", "arun"})

    def test_family_and_self_rules_share_name_precedence(self):
        profile = {
            "display_name": "Arun Shah",
            "self_patterns": [r"ARUN\s*SHAH"],
            "family_members": [
                {
                    "name": "Mira Shah",
                    "patterns": [r"\bMIRA\b"],
                    "account_head": "Mira Shah",
                }
            ],
            "accounts": [
                {"account_key": "hdfc", "bank": "hdfc", "account_id": "HDFC 1001"},
                {"account_key": "sbi", "bank": "sbi", "account_id": "SBI 2002"},
            ],
        }
        text = "UPI/CR/MIRA ARUN SHAH/SBI"
        self.assertTrue(build_dynamic_family_rules(profile)[0][2](text, 0, 100))
        self.assertFalse(
            any(r[2](text, 0, 100) for r in build_dynamic_contra_rules(profile, "hdfc"))
        )

    def test_distinct_relatives_need_review_instead_of_array_order(self):
        profile = {
            "family_members": [
                {"name": "Mira Shah", "patterns": [r"\bMIRA\b"]},
                {"name": "Arun Shah", "patterns": [r"ARUN\s*SHAH"]},
            ]
        }
        self.assertFalse(
            any(
                r[2]("MIRA SHAH TO ARUN SHAH", 100, 0)
                for r in build_dynamic_family_rules(profile)
            )
        )

    def test_atm_cash_rule_precedes_identity_transfers(self):
        from unittest.mock import patch
        from tax_automation.rules.loader import build_rule_chain

        profile = {
            "display_name": "Arun Shah",
            "self_patterns": ["ARUN"],
            "family_members": [{"name": "Mira Shah", "patterns": ["MIRA"]}],
            "accounts": [],
        }
        with patch(
            "tax_automation.rules.loader.get_entity_config", return_value=profile
        ):
            layers = build_rule_chain("example", "hdfc")
        text = "ATM-CASH MIRA ARUN SHAH"
        first = next(
            rule for layer in layers for rule in layer if rule[2](text, 100, 0)
        )
        self.assertEqual(first[0], "Cash Withdrawal")

    def test_masked_account_suffix_does_not_create_family_classification(self):
        from unittest.mock import patch
        from tax_automation.pipeline.narration import classify_transaction
        from tax_automation.rules.loader import build_rule_chain

        profile = {
            "display_name": "Arun Shah",
            "self_patterns": ["ARUN"],
            "family_members": [{"name": "Mira Shah", "patterns": ["MIRA"]}],
            "accounts": [],
        }
        with patch(
            "tax_automation.rules.loader.get_entity_config", return_value=profile
        ):
            rules = build_rule_chain("example", "hdfc")
        result = classify_transaction(
            "UPI-XXXXXXXX0094-HDFC0000001-PAYMENT", 100, 0, "example", "hdfc", rules
        )
        self.assertEqual(result[0], "UPI Payment")
