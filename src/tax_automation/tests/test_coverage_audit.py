"""Coverage diagnostics must distinguish absent money from non-monetary events."""

import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch
from openpyxl import Workbook
import pandas as pd

from tax_automation import config_loader as config
from tax_automation.tools.audit_coverage import audit, source_transactions


class TestCoverageAudit(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.cfg = self.root / "config"
        for name in ("entities", "banks", "consolidation"):
            (self.cfg / name).mkdir(parents=True)
        shutil.copytree(config.CONFIG_DIR / "schemas", self.cfg / "schemas")
        self.bank = {
            "bank_key": "demo",
            "col_date": "Date",
            "col_particulars": "Details",
            "col_dr": "Debit",
            "col_cr": "Credit",
            "col_ref": "Ref",
            "rules": [],
        }
        self.profile = {
            "entity_id": "sample",
            "display_name": "Sample Person",
            "accounts": [
                {
                    "account_key": key,
                    "bank": "demo",
                    "sheet_name": sheet,
                    "account_id": key,
                }
                for key, sheet in [
                    ("primary", "Primary"),
                    ("loan", "Rate Changes"),
                    ("missing", "Missing"),
                ]
            ],
        }
        (self.cfg / "banks/demo.json").write_text(json.dumps(self.bank))
        (self.cfg / "entities/sample.json").write_text(json.dumps(self.profile))
        (self.cfg / "consolidation/sample_fy26.json").write_text(
            json.dumps({"files": [{"filename": "all.xlsx"}]})
        )
        self.input = self.root / "data/sample/FY26/input/bank_statements"
        self.output = self.root / "data/sample/FY26/output"
        self.input.mkdir(parents=True)
        self.output.mkdir(parents=True)
        source = Workbook()
        source.active.title = "Primary"
        source.active.append(["Date", "Details", "Debit", "Credit", "Ref"])
        source.active.append(["01/05/2025", "PAYMENT", 100, 0, None])
        loan = source.create_sheet("Rate Changes")
        loan.append(["Date", "Details", "Debit", "Credit", "Ref"])
        loan.append(["01/05/2025", "RATE CHANGED", "-", None, "-"])
        source.save(self.input / "all.xlsx")
        ledger = Workbook()
        ledger.active.title = "Primary"
        ledger.active.append(
            ["Date", "Particulars", "DR", "CR", "Auto_Narration", "Account_Head", "Ref"]
        )
        ledger.active.append(["01/05/2025", "PAYMENT", 100, 0, "Known", "Known", None])
        ledger.save(self.output / "narrated_ledger.xlsx")
        for name, value in [("REPO_ROOT", self.root), ("CONFIG_DIR", self.cfg)]:
            patcher = patch.object(config, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)

    def test_full_source_inventory_and_non_monetary_coverage(self):
        result = audit("FY26")
        coverage = {r["account_key"]: r["status"] for r in result["coverage"]}
        self.assertEqual(coverage["primary"], "present")
        self.assertEqual(coverage["loan"], "non_monetary_source_only")
        self.assertEqual(coverage["missing"], "no_source_found")
        primary = next(
            r for r in result["sources"] if r.get("account_key") == "primary"
        )
        self.assertEqual(primary["missing_from_ledger"], 0)
        self.assertEqual(len(result["sources"]), 2)

    def test_signed_amount_unknown_direction_is_not_treated_as_credit(self):
        bank = {**self.bank, "col_amount": "Amount", "col_direction": "Sign"}
        frame = pd.DataFrame(
            [
                ["Date", "Details", "Amount", "Sign"],
                ["01/05/2025", "UNKNOWN", 100, "??"],
            ]
        )
        with self.assertRaisesRegex(ValueError, "direction"):
            source_transactions(frame, bank, "2025-04-01", "2026-03-31")

    def test_blank_nan_reference_is_not_a_missing_transaction(self):
        from tax_automation.tools.audit_coverage import _key

        tx = {
            "date": "2025-05-01",
            "direction": "DR",
            "cents": 100,
            "particulars": "TEST",
            "ref": "nan",
        }
        self.assertEqual(_key(tx), _key({**tx, "ref": ""}))
