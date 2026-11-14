"""Tests independent of private financial statements."""

import unittest

from tax_automation.tools.reconcile_transfers import match_transfers, _date


class TestTransferReconciliation(unittest.TestCase):
    def setUp(self):
        self.profiles = {
            "alice": {
                "display_name": "Alice Smith",
                "self_patterns": [r"ALICE(?: SMITH)?"],
                "family_members": [
                    {
                        "name": "Bob Jones",
                        "patterns": ["BOB"],
                        "account_head": "Bob Jones",
                    },
                    {
                        "name": "Bob Jones HUF",
                        "patterns": ["HUF"],
                        "account_head": "Bob Jones HUF",
                    },
                ],
            },
            "bob": {
                "display_name": "Bob Jones",
                "self_patterns": ["BOB(?: JONES)?"],
                "family_members": [
                    {
                        "name": "Alice Smith",
                        "patterns": ["ALICE"],
                        "account_head": "Alice Smith",
                    }
                ],
            },
        }

    def tx(self, key, entity, direction, text, label, day="2025-05-24", ref=""):
        return {
            "id": key,
            "entity": entity,
            "direction": direction,
            "date": day,
            "cents": 1000000,
            "amount": 10000,
            "particulars": text,
            "label": label,
            "head": label.removeprefix("Transfer - "),
            "ref": ref,
        }

    def pair(self):
        return [
            self.tx("a", "alice", "DR", "UPI BOB", "Transfer - Bob Jones"),
            self.tx("b", "bob", "CR", "UPI ALICE", "Transfer - Alice Smith"),
        ]

    def test_valid_pair_and_classification(self):
        result = match_transfers(self.pair(), self.profiles)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["status"], "matched_classification_agrees")

    def test_misclassified_opposite_side_is_discovered(self):
        txs = self.pair()
        txs[0].update(label="UPI Payment", head="Personal", particulars="PAYMENT")
        result = match_transfers(txs, self.profiles)
        self.assertEqual(result[0]["status"], "matched_review_classification")

    def test_equal_amount_alone_is_not_evidence(self):
        txs = self.pair()
        for tx in txs:
            tx.update(particulars="UNKNOWN", label="UPI", head="Personal")
        self.assertEqual(match_transfers(txs, self.profiles), [])

    def test_duplicate_amount_candidates_are_not_reused(self):
        txs = self.pair()
        txs.append(dict(txs[1], id="c"))
        result = match_transfers(txs, self.profiles)
        self.assertTrue(
            all(r["status"] == "multiple_plausible_counterparts" for r in result)
        )

    def test_shared_reference_disambiguates(self):
        txs = self.pair()
        txs[0]["ref"] = txs[1]["ref"] = "123456789012"
        txs.append(dict(txs[1], id="c", ref="987654321012"))
        result = match_transfers(txs, self.profiles)
        matched = [r for r in result if r.get("right")]
        self.assertEqual(len(matched), 1)
        self.assertEqual(matched[0]["right"]["id"], "b")

    def test_date_window_amount_and_direction(self):
        for changes in (
            {"date": "2025-06-01"},
            {"cents": 1000001},
            {"direction": "DR"},
        ):
            txs = self.pair()
            txs[1].update(changes)
            result = match_transfers(txs, self.profiles)
            self.assertFalse(any(r.get("right") for r in result))
        self.assertEqual(_date("24/05/25").isoformat(), "2025-05-24")

    def test_huf_is_not_bob_personally(self):
        txs = self.pair()
        txs[0]["particulars"] = "BOB JONES HUF"
        result = match_transfers(txs, self.profiles)
        self.assertFalse(any(r.get("right") for r in result))

    def test_classification_without_raw_evidence_does_not_prove_pair(self):
        txs = self.pair()
        for tx in txs:
            tx["particulars"] = "UNKNOWN"
        result = match_transfers(txs, self.profiles)
        self.assertTrue(all(r["status"] == "no_matching_entry" for r in result))

    def test_sip_lookalike_is_rejected_even_with_matching_reference(self):
        txs = self.pair()
        txs[0]["particulars"] = "ACH D- FUND SIP BOB"
        for tx in txs:
            tx["ref"] = "123456789012"
        result = match_transfers(txs, self.profiles)
        self.assertFalse(any(r.get("right") for r in result))
        self.assertTrue(
            any(
                c["reason"] == "non_transfer_description"
                for r in result
                for c in r["rejected_candidates"]
            )
        )

    def test_reference_conflict_rejects_name_amount_and_date_match(self):
        txs = self.pair()
        txs[0]["ref"], txs[1]["ref"] = "123456789012", "987654321012"
        result = match_transfers(txs, self.profiles)
        self.assertFalse(any(r.get("right") for r in result))
        self.assertEqual(
            result[0]["rejected_candidates"][0]["reason"],
            "conflicting_payment_references",
        )

    def test_strong_match_removes_weak_candidate_from_ambiguity(self):
        txs = self.pair()
        txs[0]["ref"] = txs[1]["ref"] = "123456789012"
        txs.append(
            dict(
                txs[0],
                id="lookalike",
                particulars="UPI UNKNOWN",
                label="UPI Payment",
                head="Personal",
                ref="",
            )
        )
        result = match_transfers(txs, self.profiles)
        leftover = next(r for r in result if r["left"]["id"] == "lookalike")
        self.assertEqual(leftover["status"], "rejected_weaker_candidates")
        self.assertEqual(leftover["candidates"], [])

    def test_same_entity_transfers_match_in_separate_scope(self):
        txs = self.pair()
        for index, tx in enumerate(txs):
            tx.update(
                entity="alice",
                sheet=f"Bank {index}",
                particulars="NEFT ALICE SMITH",
                ref="123456789012",
            )
        result = match_transfers(txs, self.profiles)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["scope"], "self")

    def test_external_family_name_prevents_self_match(self):
        txs = self.pair()
        for index, tx in enumerate(txs):
            tx.update(
                entity="alice",
                sheet=f"Bank {index}",
                particulars="NEFT ALICE BOB JONES HUF",
                ref="123456789012",
            )
        result = match_transfers(txs, self.profiles)
        self.assertFalse(any(r.get("right") for r in result))

    def add_accounts(self):
        self.profiles["alice"]["accounts"] = [
            {"account_key": "a1", "sheet_name": "A1", "bank": "bank_a"}
        ]
        self.profiles["bob"]["accounts"] = [
            {
                "account_key": "b1",
                "sheet_name": "B1",
                "bank": "bank_b",
                "account_number": "1234567891234",
            },
            {"account_key": "b2", "sheet_name": "B2", "bank": "bank_b"},
        ]

    def test_identified_missing_account_has_specific_coverage_status(self):
        self.add_accounts()
        tx = self.pair()[0]
        tx["particulars"] = "NEFT BOB 1234567891234"
        result = match_transfers(
            [tx], self.profiles, coverage=[{"entity": "bob", "account_key": "b2"}]
        )
        self.assertEqual(result[0]["status"], "counterparty_account_unavailable")

    def test_unknown_account_with_missing_coverage_is_not_classification_error(self):
        self.add_accounts()
        result = match_transfers([self.pair()[0]], self.profiles)
        self.assertEqual(result[0]["status"], "counterparty_coverage_incomplete")

    def test_account_suffix_does_not_identify_destination(self):
        from tax_automation.tools.transfer_matching import account_mentions

        self.add_accounts()
        tx = self.pair()[0]
        tx["particulars"] = "UPI-XXXXXXXXXX1234"
        self.assertEqual(account_mentions(tx, self.profiles), set())

    def test_full_account_conflict_rejects_candidate(self):
        self.add_accounts()
        txs = self.pair()
        txs[0]["particulars"] = "NEFT BOB 1234567891234"
        txs[1]["account_key"] = "b2"
        result = match_transfers(txs, self.profiles)
        self.assertFalse(any(r.get("right") for r in result))

    def test_purpose_conflict_prevents_match(self):
        txs = self.pair()
        txs[0]["particulars"] = "UPI BOB GIFT"
        txs[1]["particulars"] = "UPI ALICE REPAYMENT"
        result = match_transfers(txs, self.profiles)
        self.assertFalse(any(r.get("right") for r in result))

    def test_reference_is_extracted_from_narration_not_account_numbers(self):
        from tax_automation.tools.transfer_matching import references, settings

        tx = self.pair()[0]
        tx["particulars"] = "NEFT UTR NO: SBIN525101803729 1234567891234"
        self.assertEqual(references(tx, settings()), {"SBIN525101803729"})

    def test_suggestions_preserve_original_classifications(self):
        from copy import deepcopy

        txs = self.pair()
        txs[0].update(label="UPI Payment", head="Personal")
        txs[0]["ref"] = txs[1]["ref"] = "123456789012"
        original = deepcopy(txs)
        result = match_transfers(txs, self.profiles)
        suggestion = result[0]["proposed_corrections"][0]
        self.assertEqual(suggestion["previous_label"], "UPI Payment")
        self.assertEqual(suggestion["proposed_label"], "Transfer - Bob Jones")
        self.assertFalse(suggestion["applied"])
        self.assertEqual(suggestion["counterpart_row"], "b")
        self.assertEqual(txs, original)

    def test_order_independent_matching(self):
        txs = self.pair()
        txs[0]["ref"] = txs[1]["ref"] = "123456789012"
        txs.append(dict(txs[0], id="lookalike", ref=""))

        def pairs(rows):
            return {
                frozenset((r["left"]["id"], r["right"]["id"]))
                for r in match_transfers(rows, self.profiles)
                if r.get("right")
            }

        self.assertEqual(pairs(txs), pairs(list(reversed(txs))))

    def test_bank_destination_conflict_rejects_even_shared_reference(self):
        self.add_accounts()
        self.profiles["bob"]["accounts"][0]["bank"] = "hdfc"
        txs = self.pair()
        txs[0]["particulars"] = "NEFT DR-SBIN0011669-BOB"
        txs[1]["account_key"] = "b1"
        for tx in txs:
            tx["ref"] = "123456789012"
        result = match_transfers(txs, self.profiles)
        self.assertFalse(any(r.get("right") for r in result))
        self.assertEqual(
            result[0]["rejected_candidates"][0]["reason"], "counterparty_bank_conflict"
        )

    def test_legacy_sheet_alias_is_explicit_and_ambiguous_bank_is_unbound(self):
        from tax_automation.tools.transfer_matching import account_for_sheet

        self.add_accounts()
        self.profiles["bob"]["accounts"][0]["sheet_aliases"] = ["Legacy"]
        self.assertEqual(
            account_for_sheet(self.profiles["bob"], "Legacy")["account_key"], "b1"
        )
        self.assertIsNone(account_for_sheet(self.profiles["bob"], "bank_b"))

    def test_reference_extraction_does_not_use_ifsc_as_payment_reference(self):
        from tax_automation.tools.transfer_matching import references, settings

        tx = self.pair()[0]
        tx["particulars"] = "UPI BOB HDFC0000167"
        self.assertEqual(references(tx, settings()), set())

    def test_highest_reference_tie_is_not_resolved_by_lower_evidence(self):
        txs = self.pair()
        txs[0]["ref"] = txs[1]["ref"] = "123456789012"
        txs.append(dict(txs[1], id="second_credit"))
        txs.append(dict(txs[0], id="weaker_debit", ref=""))
        result = match_transfers(txs, self.profiles)
        self.assertFalse(any(r.get("right") for r in result))

    def test_full_vpa_requires_exact_boundaries(self):
        from tax_automation.tools.transfer_matching import account_mentions

        self.add_accounts()
        self.profiles["bob"]["accounts"][0]["vpas"] = ["bob@bank"]
        tx = self.pair()[0]
        tx["particulars"] = "UPI/bob@bank-other/TRANSFER"
        self.assertEqual(account_mentions(tx, self.profiles), set())
        tx["particulars"] = "UPI/bob@bank/TRANSFER"
        self.assertEqual(account_mentions(tx, self.profiles), {("bob", "b1")})

    def test_fiscal_period_boundaries_and_full_year_alias(self):
        from tax_automation.tools.reconcile_transfers import fiscal_period

        expected = ("2025-04-01", "2026-03-31")
        self.assertEqual(fiscal_period("FY26"), expected)
        self.assertEqual(fiscal_period("FY2026"), expected)
        with self.assertRaises(ValueError):
            fiscal_period("FY026")

    def test_atm_withdrawal_never_pairs_with_named_receipt(self):
        txs = self.pair()
        txs[0].update(
            particulars="ATM-CASH-AXIS/NASHIK", label="What is this?", head="Suspense"
        )
        result = match_transfers(txs, self.profiles)
        self.assertFalse(any(r.get("right") for r in result))

    def test_compound_name_does_not_create_two_counterparties(self):
        from tax_automation.tools.reconcile_transfers import _targets

        profiles = {
            "source": {"display_name": "Alice Brown", "family_members": []},
            "mira": {"display_name": "Mira Shah", "self_patterns": ["MIRA"]},
            "arun": {"display_name": "Arun Shah", "self_patterns": [r"ARUN\s*SHAH"]},
        }
        tx = self.tx("row", "source", "DR", "MRS. MIRA ARUN SHAH", "Transfer")
        self.assertEqual(_targets(tx, profiles), {"mira"})
