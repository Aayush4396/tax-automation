# -*- coding: utf-8 -*-
"""test_pipeline.py.

Integration tests for the pipeline modules.
"""

from __future__ import annotations
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from openpyxl import Workbook

from tax_automation.pipeline.consolidation import consolidate_entity
from tax_automation.pipeline.narration import process_entity_narration


class TestNarrationPipeline(unittest.TestCase):
    """Integration tests for the narration pipeline."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.test_data_dir = Path(self.temp_dir.name)

        # Create a sample input file with required columns
        self.input_file = self.test_data_dir / "test_input.xlsx"
        wb = Workbook()
        ws = wb.active
        ws.title = "HDFC Bank"
        # Add headers
        headers = ["Date", "Particulars", "Debit", "Credit", "Balance"]
        ws.append(headers)
        # Add sample data
        ws.append(["2026-04-01", "Salary", "50000", "0", "50000"])
        wb.save(self.input_file)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_process_entity_narration(self):
        """Test the narration pipeline with sample data."""
        with (
            patch("tax_automation.config_loader.get_entity_config") as mock_config,
            patch("tax_automation.pipeline.narration.identify_bank") as mock_identify,
            patch(
                "tax_automation.pipeline.narration.find_header_row"
            ) as mock_find_header,
        ):
            # Setup mocks
            mock_config.return_value = {
                "display_name": "Test Entity",
                "banks": {
                    "hdfc": {
                        "display_name": "HDFC Bank",
                        "account_id": "HDFC 5413",
                        "col_date": "Date",
                        "col_particulars": "Particulars",
                        "col_dr": "Debit",
                        "col_cr": "Credit",
                        "col_balance": "Balance",
                    }
                },
            }
            mock_identify.return_value = ("hdfc", 0.9)
            mock_find_header.return_value = 0

            # Run the narration pipeline
            output_file = self.test_data_dir / "test_output.xlsx"
            result = process_entity_narration(
                entity_id="test",
                fy="FY26",
                input_path=self.input_file,
                output_path=output_file,
            )

            # Verify results
            self.assertEqual(result, output_file)
            self.assertTrue(output_file.exists())


class TestConsolidationPipeline(unittest.TestCase):
    """Integration tests for the consolidation pipeline."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.test_data_dir = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_consolidate_entity(self):
        """Test the consolidation pipeline with sample data."""
        with (
            patch("tax_automation.config_loader.get_entity_config") as mock_config,
            patch(
                "tax_automation.pipeline.consolidation.consolidate_entity_statements"
            ) as mock_consolidate,
        ):
            mock_config.return_value = {"display_name": "Test Entity"}
            expected_out = self.test_data_dir / "consolidated_statements.xlsx"
            mock_consolidate.return_value = expected_out

            result = consolidate_entity(
                entity_id="test",
                fy="FY26",
                input_dir=self.test_data_dir,
                output_dir=self.test_data_dir,
            )

            self.assertEqual(result, expected_out)


if __name__ == "__main__":
    unittest.main()
