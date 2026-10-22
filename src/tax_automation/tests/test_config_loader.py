# -*- coding: utf-8 -*-
"""test_config_loader.py.

Unit tests for config_loader:
- get_entity_config
- get_bank_schema
- resolve_entity_bank_registry
- resolve_input_dir / resolve_output_dir
"""

import unittest
from pathlib import Path

from tax_automation.config_loader import (
    get_entity_config,
    get_bank_schema,
    resolve_entity_bank_registry,
    resolve_input_dir,
    resolve_output_dir,
    get_merchants_config,
    get_cc_categories_config,
)


class TestConfigLoader(unittest.TestCase):
    """Test suite for configuration loading and validation."""

    def test_get_entity_config_exists(self):
        cfg = get_entity_config("aayush")
        self.assertEqual(cfg["entity_id"], "aayush")
        self.assertIn("display_name", cfg)
        self.assertIn("accounts", cfg)

    def test_get_entity_config_nonexistent(self):
        with self.assertRaises(FileNotFoundError):
            get_entity_config("nonexistent_entity_12345")

    def test_get_bank_schema(self):
        hdfc = get_bank_schema("hdfc")
        self.assertEqual(hdfc.get("bank_key"), "hdfc")
        self.assertIn("header_signals", hdfc)
        self.assertIn("meta_signals", hdfc)

    def test_resolve_entity_bank_registry(self):
        reg = resolve_entity_bank_registry("aayush")
        self.assertIsInstance(reg, dict)
        self.assertTrue(len(reg) > 0)
        # Verify merged keys
        first_acc = next(iter(reg.values()))
        self.assertIn("account_id", first_acc)
        self.assertIn("sheet_name", first_acc)
        self.assertIn("bank_type", first_acc)

    def test_path_resolvers(self):
        in_p = resolve_input_dir("aayush", "FY26", "bank_statements")
        self.assertIsInstance(in_p, Path)
        self.assertTrue(in_p.exists())

        out_p = resolve_output_dir("aayush", "FY26")
        self.assertIsInstance(out_p, Path)
        self.assertTrue(out_p.exists())

    def test_merchants_and_cc_categories(self):
        merchants = get_merchants_config()
        self.assertIsInstance(merchants, list)
        self.assertTrue(len(merchants) > 0)

        cc_cats = get_cc_categories_config()
        self.assertIsInstance(cc_cats, dict)
        self.assertIn("categories", cc_cats)


if __name__ == "__main__":
    unittest.main()
