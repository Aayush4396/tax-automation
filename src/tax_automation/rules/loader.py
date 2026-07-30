# -*- coding: utf-8 -*-
"""
loader.py
=========
Assembles runtime rule chains: entity_extensions + bank_base + common_base.
"""

from __future__ import annotations
import importlib
from tax_automation.rules.common_base import RULES_COMMON

_BANK_RULES_CACHE: dict[str, list[tuple]] = {}
_EXT_CACHE: dict[str, dict[str, list[tuple]]] = {}


def load_entity_extensions(entity_id: str) -> dict[str, list[tuple]]:
    """Loads entity rule extensions dynamically."""
    if entity_id in _EXT_CACHE:
        return _EXT_CACHE[entity_id]
        
    module_name = f"tax_automation.rules.entity_extensions.{entity_id.lower()}_rules"
    try:
        mod = importlib.import_module(module_name)
        ext = getattr(mod, "EXTRA_RULES", {})
    except (ImportError, AttributeError):
        ext = {}
        
    _EXT_CACHE[entity_id] = ext
    return ext


def load_bank_rules(bank_key: str) -> list[tuple]:
    """Loads bank base classification rules."""
    key = bank_key.lower()
    if key in _BANK_RULES_CACHE:
        return _BANK_RULES_CACHE[key]
        
    # Map bank keys (e.g. hdfc, sbi_ca, sbi_od -> hdfc_base, sbi_base)
    base_module_map = {
        "hdfc": "hdfc_base",
        "sbi": "sbi_base",
        "sbi_ca": "sbi_base",
        "sbi_od": "sbi_base",
        "sbi_nsk": "sbi_base",
        "sbi_kota": "sbi_base",
        "sbi_rawatbhata": "sbi_base",
        "sbi_ins_loan": "sbi_base",
        "sbi_flat_ins": "sbi_base",
        "sbi_bank_3479": "sbi_base",
        "kotak": "kotak_base",
        "axis": "axis",
        "federal": "federal",
        "sbm": "sbm",
        "boi": "boi",
        "huf_ca": "huf",
        "huf": "huf",
    }
    
    mod_subname = base_module_map.get(key, key)
    module_name = f"tax_automation.rules.banks.{mod_subname}"
    attr_name = f"RULES_{mod_subname.upper()}"
    
    try:
        mod = importlib.import_module(module_name)
        rules = getattr(mod, attr_name, [])
        if not rules:
            # Fallback to any list[tuple] defined in module
            for var_name in dir(mod):
                if var_name.startswith("RULES_") and isinstance(getattr(mod, var_name), list):
                    rules = getattr(mod, var_name)
                    break
    except (ImportError, AttributeError):
        rules = []
        
    _BANK_RULES_CACHE[key] = rules
    return rules


def build_rule_chain(entity_id: str, bank_key: str) -> tuple[list[tuple], list[tuple]]:
    """
    Builds the full rule chain for a transaction:
    Returns (bank_rules, common_rules)
    """
    ext = load_entity_extensions(entity_id)
    bank_ext = ext.get(bank_key.lower(), [])
    common_ext = ext.get("common", [])
    
    bank_base = load_bank_rules(bank_key)
    
    full_bank_rules = bank_ext + bank_base
    full_common_rules = common_ext + RULES_COMMON
    
    return full_bank_rules, full_common_rules
