"""Reviewed corrections require exact transaction identity and explicit approval."""

from copy import deepcopy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from openpyxl import Workbook, load_workbook
from tax_automation.core.reviewed_corrections import (
    apply_corrections,
    narration_hash,
    update_existing_ledger,
)


class TestReviewedCorrections(unittest.TestCase):
    def setUp(self):
        self.record = {
            "TX_Date": "24/05/25",
            "Bank_Key": "bank_a",
            "DR": 100,
            "CR": 0,
            "Ref": "000123456789012",
            "Particulars": "UPI-MASKED-123456789012-PAYMENT",
            "Auto_Narration": "UPI Payment",
            "Account_Head": "Personal",
        }
        self.correction = {
            "id": "review1",
            "approved": True,
            "entity": "sample",
            "fy": "FY26",
            "label": "Transfer - Other Person",
            "head": "Other Person",
            "selector": {
                "date": "2025-05-24",
                "direction": "DR",
                "cents": 10000,
                "reference": "123456789012",
                "account_key": "bank_a",
                "narration_sha256": narration_hash(self.record["Particulars"]),
            },
        }

    def test_exact_identity_and_unchanged_money(self):
        record = deepcopy(self.record)
        audit = apply_corrections([record], [self.correction])
        self.assertEqual(record["Auto_Narration"], "Transfer - Other Person")
        self.assertEqual((record["DR"], record["CR"]), (100, 0))
        self.assertEqual(audit[0]["before_label"], "UPI Payment")
        self.assertEqual(len(apply_corrections([record], [self.correction])), 1)

    def test_suffix_amount_date_and_account_do_not_leak_to_other_rows(self):
        for delta in (
            {"DR": 101},
            {"TX_Date": "25/05/25"},
            {"Bank_Key": "bank_b"},
            {"Particulars": "UPI-OTHER-123456789012-PAYMENT"},
        ):
            record = {**self.record, **delta}
            self.assertEqual(apply_corrections([record], [self.correction]), [])

    def test_duplicate_rows_fail(self):
        with self.assertRaises(ValueError):
            apply_corrections(
                [deepcopy(self.record), deepcopy(self.record)], [self.correction]
            )

    def test_patch_all_copies_preserves_notes_and_formulas(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "ledger.xlsx"
            wb = Workbook()
            wb.remove(wb.active)
            for name in ("Bank A", "For Tally", "Conso"):
                ws = wb.create_sheet(name)
                ws.append(
                    [
                        "TX Date",
                        "Particulars",
                        "Ref",
                        "DR",
                        "CR",
                        "Auto_Narration",
                        "Account_Head",
                        "Account No",
                        "Review Remarks",
                    ]
                )
                ws.append(
                    [
                        "24/05/25",
                        self.record["Particulars"],
                        self.record["Ref"],
                        100,
                        0,
                        "UPI Payment",
                        "Personal",
                        "Bank A",
                        "keep note",
                    ]
                )
            wb.create_sheet("Summary")["A1"] = "=SUM('Bank A'!D2:D2)"
            wb.save(path)
            profile = {
                "accounts": [
                    {
                        "account_key": "bank_a",
                        "account_id": "Bank A",
                        "sheet_name": "Bank A",
                        "bank": "a",
                    }
                ]
            }
            with (
                patch(
                    "tax_automation.core.reviewed_corrections.load_corrections",
                    return_value=[self.correction],
                ),
                patch(
                    "tax_automation.config_loader.get_entity_config",
                    return_value=profile,
                ),
            ):
                audit = update_existing_ledger(path, "sample", "FY26")
            self.assertEqual(len(audit), 3)
            result = load_workbook(path)
            for name in ("Bank A", "For Tally", "Conso"):
                self.assertEqual(result[name]["F2"].value, self.correction["label"])
                self.assertEqual(result[name]["I2"].value, "keep note")
            self.assertEqual(result["Summary"]["A1"].value, "=SUM('Bank A'!D2:D2)")
            result.close()

    def test_unapproved_override_is_rejected(self):
        correction = {**self.correction, "approved": False}
        with self.assertRaises(ValueError):
            apply_corrections([deepcopy(self.record)], [correction])
