# -*- coding: utf-8 -*-
"""
cc_category_map.py
==================
Maps Kotak CC statement SpendsArea categories → (Auto_Narration, Account_Head)
and hex fill colors, loaded dynamically from config/cc_categories.json.
"""

from tax_automation.config_loader import get_cc_categories_config

_cfg = get_cc_categories_config()

_raw_narration_map = _cfg.get("narration_map", {})
CC_NARRATION_MAP: dict[str, tuple[str, str]] = {
    k: (v[0], v[1]) for k, v in _raw_narration_map.items()
}

CC_COLOUR_MAP: dict[str, str] = _cfg.get("colour_map", {})


def map_category(cc_category: str) -> tuple[str, str]:
    """Return (Auto_Narration, Account_Head) for a CC SpendsArea string."""
    return CC_NARRATION_MAP.get(cc_category, (f"CC - {cc_category}", "Miscellaneous"))
