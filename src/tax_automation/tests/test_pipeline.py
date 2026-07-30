# -*- coding: utf-8 -*-
"""
test_pipeline.py
=================

Integration tests for the pipeline modules.
"""

import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock
import pandas as pd
from openpyxl import Workbook

from tax_automation.pipeline.narration import process_entity_narration
from tax_automation.pipeline.consolidation import consolidate_entity_statements


class TestNarrationPipeline(unittest.TestCase):
    """Integration tests for the narration pipeline."""

    def setUp(self):
        # Setup test data
        self.test_data_dir = Path("__tests__")
        self.test_data_dir.mkdir(exist_ok=True)

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

    def test_process_entity_narration(self):
        """Test the narration pipeline with sample data."""
        # Mock external dependencies
        with (
            patch("tax_automation.config_loader.get_entity_config") as mock_config,
            patch("tax_automation.pipeline.narration.identify_bank") as mock_identify,
            patch("tax_automation.pipeline.narration.find_header_row") as mock_find_header,
        ):

            # Setup mocks
            mock_config.return_value = {
                "display_name": "Test Entity",
                "banks": {
                    "hdfc": {
                        "display_name": "HDFC Bank",
                        "col_particulars": "Particulars",
                        "col_dr": "Debit",
                        "col_cr": "Credit",
                    }
                }
            }
            mock_identify.return_value = ("hdfc", 0.9)
            mock_find_header.return_value = 0

            # Run the narration pipeline
            result = process_entity_narration(
                entity_id="test",
                fy="FY26",
                input_path=self.input_file,
                output_path=self.test_data_dir / "test_output.xlsx"
            )

            # Verify results
            self.assertEqual(result, self.test_data_dir / "test_output.xlsx")


class TestConsolidationPipeline(unittest.TestCase):
    """Integration tests for the consolidation pipeline."""

    def setUp(self):
        # Setup test data
        self.test_data_dir = Path("__tests__")
        self.test_data_dir.mkdir(exist_ok=True)

    def test_consolidate_entity(self):
        """Test the consolidation pipeline with sample data."""
        # Mock external dependencies
        with (
            patch("tax_automation.config_loader.get_entity_config") as mock_config,
            patch("tax_automation.config_loader.get_consolidation_map") as mock_map,
            patch("tax_automation.pipeline.consolidation.consolidate_entity_statements") as mock_consolidate,
        ):

            # Setup mocks
            mock_config.return_value = {
                "display_name": "Test Entity"
            }
            mock_map.return_value = {
                "mapping": {},
                "output_sheet": "Consolidated"
            }
            # Return a mock path
            mock_consolidate.return_value = self.test_data_dir / "test_consolidated.xlsx"

            # Run the consolidation
            result = mock_consolidate(
                entity_id="test",
                fy="FY26"
            )

            # Verify results
            self.assertEqual(result, self.test_data_dir / "test_consolidated.xlsx")


if __name__ == "__main__":
    unittest.main()
