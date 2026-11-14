"""Regression coverage for onboarding unseen entities, banks and file layouts."""

import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from openpyxl import Workbook, load_workbook
from tax_automation import config_loader as config
from tax_automation.consolidators.generic_consolidator import load_file_to_df
from tax_automation.core.bank_identifier import identify_bank
from tax_automation.pipeline.narration import process_entity_narration
from tax_automation.rules.loader import build_rule_chain, build_dynamic_contra_rules


class TestOnboarding(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.cfg = self.root / "config"
        for folder in ("banks", "entities"):
            (self.cfg / folder).mkdir(parents=True)
        shutil.copytree(config.CONFIG_DIR / "schemas", self.cfg / "schemas")
        for file in config.CONFIG_DIR.glob("*.json"):
            shutil.copy(file, self.cfg / file.name)
        self.bank = {
            "bank_key": "newbank",
            "display_name": "New Bank",
            "rules": [
                {
                    "label": "New Income",
                    "account_head": "Income",
                    "pattern": "NEWPAY",
                    "direction": "CR",
                    "confidence": 0.95,
                }
            ],
            "meta_signals": ["NEW BANK"],
            "header_signals": ["Date", "Details", "Debit", "Credit"],
            "col_date": "Date",
            "col_particulars": "Details",
            "col_dr": "Debit",
            "col_cr": "Credit",
            "col_balance": "Balance",
            "alias_tokens": ["NEWBANK"],
        }
        self.entity = {
            "entity_id": "newperson",
            "display_name": "New Person",
            "self_patterns": ["NEW PERSON"],
            "accounts": [
                {
                    "account_key": "primary",
                    "bank": "newbank",
                    "account_id": "NEW 1111",
                    "sheet_name": "Primary",
                },
                {
                    "account_key": "secondary",
                    "bank": "newbank",
                    "account_id": "NEW 2222",
                    "sheet_name": "Secondary",
                },
            ],
        }
        self.write("banks/newbank.json", self.bank)
        self.write("entities/newperson.json", self.entity)
        self.patcher = patch.object(config, "CONFIG_DIR", self.cfg)
        self.patcher.start()
        self.addCleanup(self.patcher.stop)

    def write(self, name, value):
        (self.cfg / name).write_text(json.dumps(value), encoding="utf-8")

    def test_new_entity_bank_and_two_accounts_end_to_end(self):
        source = self.root / "input.xlsx"
        wb = Workbook()
        wb.remove(wb.active)
        for name in ("Primary", "Secondary"):
            ws = wb.create_sheet(name)
            ws.append(["Date", "Details", "Debit", "Credit", "Balance"])
            ws.append(["2026-04-01", "NEWPAY", 0, 100, 100])
        wb.save(source)
        output = self.root / "output.xlsx"
        process_entity_narration("newperson", "FY26", source, output)
        result = load_workbook(output, data_only=False)
        self.addCleanup(result.close)
        for name in ("Primary", "Secondary"):
            values = [cell for row in result[name].values for cell in row]
            self.assertIn("New Income", values)
        self.assertIn("Tally Vouchers", result.sheetnames)

    def test_live_bank_and_common_rule_edits(self):
        before = build_rule_chain("newperson", "primary")
        self.assertEqual(before[0][-1][0], "New Income")
        self.bank["rules"][0]["label"] = "Changed Income"
        self.write("banks/newbank.json", self.bank)
        self.write(
            "rules_common.json",
            [{"label": "New Common", "account_head": "Other", "pattern": "FRESH"}],
        )
        after = build_rule_chain("newperson", "primary")
        self.assertEqual(after[0][-1][0], "Changed Income")
        self.assertEqual(after[1][0][0], "New Common")

    def test_invalid_rules_and_duplicate_accounts_fail(self):
        self.bank["rules"][0]["pattern"] = "["
        self.write("banks/newbank.json", self.bank)
        with self.assertRaises(ValueError):
            build_rule_chain("newperson", "primary")
        self.entity["accounts"][1]["account_key"] = "primary"
        self.write("entities/newperson.json", self.entity)
        with self.assertRaises(ValueError):
            config.resolve_entity_bank_registry("newperson")

    def test_ambiguous_accounts_and_unknown_bank(self):
        registry = config.resolve_entity_bank_registry("newperson")
        rows = [["Date", "Details", "Debit", "Credit"]]
        self.assertEqual(identify_bank(rows, 0, registry, "Unbound")[0], "unknown")
        self.assertEqual(identify_bank(rows, 0, registry, "Secondary")[0], "secondary")
        with self.assertRaises(FileNotFoundError):
            config.get_bank_schema("typo")

    def test_same_bank_contra_needs_account_digits(self):
        rules = build_dynamic_contra_rules(self.entity, "primary")
        target = next(rule for rule in rules if rule[1] == "NEW 2222")
        self.assertFalse(target[2]("NEW PERSON NEWBANK", 10, 0))
        self.assertTrue(target[2]("NEW PERSON NEWBANK 2222", 10, 0))

    def test_csv_multiline_delimiter_and_excel_sheet_selection(self):
        source = self.root / "input.csv"
        source.write_text('Date;Details;Credit\n2026-04-01;"two\nlines";100\n')
        df, _ = load_file_to_df(source, delimiter=";")
        self.assertEqual(df.iloc[1, 1].replace("\r\n", "\n"), "two\nlines")
        wb = Workbook()
        wb.active.append(["first"])
        wb.create_sheet("Transactions").append(["second"])
        excel = self.root / "multiple.xlsx"
        wb.save(excel)
        with self.assertRaises(ValueError):
            load_file_to_df(excel)
        df, _ = load_file_to_df(excel, source_sheet="Transactions")
        self.assertEqual(df.iloc[0, 0], "second")

    def test_pdf_reads_all_pages_and_removes_repeated_headers(self):
        header = ["Date", "Details", "Credit"]
        pages = []
        for amount in ("100", "200"):
            page = MagicMock()
            page.extract_tables.return_value = [
                [header, ["2026-04-01", "NEWPAY", amount]]
            ]
            page.extract_text.return_value = "NEW BANK"
            pages.append(page)
        target = "tax_automation.consolidators.generic_consolidator.pdfplumber.open"
        with patch(target) as opened:
            opened.return_value.__enter__.return_value.pages = pages
            df, rows = load_file_to_df(self.root / "input.pdf")
        self.assertEqual(rows.count(header), 1)
        self.assertEqual(df.iloc[-1, -1], "200")

    def test_missing_file_does_not_create_output(self):
        from tax_automation.consolidators.generic_consolidator import (
            consolidate_entity_statements,
        )

        mapping = {"files": [{"filename": "missing.csv", "sheet_name": "Primary"}]}
        with patch(
            "tax_automation.consolidators.generic_consolidator.get_consolidation_map",
            return_value=mapping,
        ):
            with self.assertRaises(FileNotFoundError):
                consolidate_entity_statements("newperson", "FY26", self.root, self.root)
        self.assertFalse((self.root / "consolidated_statements.xlsx").exists())

    def test_unknown_sheet_and_missing_columns_fail(self):
        source = self.root / "invalid.xlsx"
        output = self.root / "invalid_output.xlsx"
        wb = Workbook()
        ws = wb.active
        ws.title = "Unbound"
        ws.append(["Date", "Details", "Debit", "Credit"])
        ws.append(["2026-04-01", "NEWPAY", 0, 100])
        wb.save(source)
        with self.assertRaisesRegex(ValueError, "Cannot resolve account"):
            process_entity_narration("newperson", "FY26", source, output)
        ws.title = "Primary"
        ws.cell(1, 4, "Unexpected")
        wb.save(source)
        with self.assertRaisesRegex(ValueError, "missing column"):
            process_entity_narration("newperson", "FY26", source, output)
        self.assertFalse(output.exists())

    def test_consolidation_imports_all_sheets_including_hidden(self):
        from tax_automation.consolidators.generic_consolidator import (
            consolidate_entity_statements,
        )

        source = self.root / "many.xlsx"
        wb = Workbook()
        wb.remove(wb.active)
        for name in ("Primary", "Secondary"):
            ws = wb.create_sheet(name)
            ws.append(["Date", "Details", "Debit", "Credit"])
            ws.append(["2026-04-01", "NEWPAY", 0, 100])
        wb["Secondary"].sheet_state = "hidden"
        wb.create_sheet("Empty")
        wb.save(source)
        mapping = {"files": [{"filename": source.name, "sheet_name": "Primary"}]}
        with patch(
            "tax_automation.consolidators.generic_consolidator.get_consolidation_map",
            return_value=mapping,
        ):
            output = consolidate_entity_statements(
                "newperson", "FY26", self.root, self.root
            )
        result = load_workbook(output, read_only=True)
        self.addCleanup(result.close)
        self.assertEqual(result.sheetnames, ["Primary", "Secondary"])
        manifest = json.loads((self.root / "consolidation_manifest.json").read_text())
        self.assertEqual(len(manifest["sheets"]), 3)
        self.assertEqual(manifest["sheets"][-1]["reason"], "empty worksheet")

    def test_all_sheets_explicit_selection_and_exclusions_are_audited(self):
        from tax_automation.consolidators.generic_consolidator import (
            load_statement_sheets,
        )

        source = self.root / "selection.xlsx"
        wb = Workbook()
        wb.active.title = "Primary"
        wb.active.append(["one"])
        wb.create_sheet("Secondary").append(["two"])
        wb.save(source)
        rows = load_statement_sheets(source, spec={"source_sheet": "Secondary"})
        self.assertIsNone(rows[0][1])
        self.assertIsNotNone(rows[0][2])
        self.assertEqual(rows[1][1].iloc[0, 0], "two")
        with self.assertRaises(ValueError):
            load_statement_sheets(source, spec={"exclude_sheets": ["Typo"]})

    def test_shared_amount_direction_column_uses_transaction_not_balance_sign(self):
        self.bank.update(
            col_amount="Amount", col_direction="Dr / Cr", direction_column_occurrence=0
        )
        self.write("banks/newbank.json", self.bank)
        source = self.root / "signed.xlsx"
        wb = Workbook()
        ws = wb.active
        ws.title = "Primary"
        ws.append(["Date", "Details", "Amount", "Dr / Cr", "Balance", "Dr / Cr"])
        ws.append(["2026-04-01", "DEBIT", 70, "DR", 30, "CR"])
        ws.append(["2026-04-02", "NEWPAY", 20, "CR", 50, "DR"])
        wb.save(source)
        output = self.root / "signed_output.xlsx"
        process_entity_narration("newperson", "FY26", source, output)
        result = load_workbook(output, read_only=True)
        self.addCleanup(result.close)
        values = list(result["Primary"].values)
        header_row = next(i for i, row in enumerate(values) if "Auto_Narration" in row)
        header = list(values[header_row])
        records = values[header_row + 1 : header_row + 3]
        self.assertEqual([r[header.index("DR")] for r in records], [70, 0])
        self.assertEqual([r[header.index("CR")] for r in records], [0, 20])

    def test_unresolved_nonempty_worksheet_blocks_incomplete_import(self):
        from tax_automation.consolidators.generic_consolidator import (
            consolidate_entity_statements,
        )

        source = self.root / "unknown.xlsx"
        wb = Workbook()
        wb.active.title = "Primary"
        wb.active.append(["Date", "Details", "Debit", "Credit"])
        wb.active.append(["2026-04-01", "NEWPAY", 0, 100])
        wb.create_sheet("Unmapped Notes").append(["Unrecognized contents"])
        wb.save(source)
        with patch(
            "tax_automation.consolidators.generic_consolidator.get_consolidation_map",
            return_value={"files": [{"filename": source.name}]},
        ):
            with self.assertRaisesRegex(ValueError, "Cannot resolve source sheet"):
                consolidate_entity_statements("newperson", "FY26", self.root, self.root)
        self.assertFalse((self.root / "consolidated_statements.xlsx").exists())
