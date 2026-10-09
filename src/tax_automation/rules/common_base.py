# -*- coding: utf-8 -*-
"""
common_base.py
==============
Cross-bank narration rules applied to ALL banks, after bank-specific rules.
All rules are loaded dynamically from config/rules_common.json.

Rule tuple format: (label, account_head, match_fn(p, dr, cr) -> bool, confidence)

Priority: top → bottom, first match wins.
The final rule is always the fallback: "What is this?"
"""

from __future__ import annotations
import re
from tax_automation.config_loader import get_declarative_common_rules


def _compile_declarative_rule(r_dict: dict) -> tuple:
    label = r_dict["label"]
    head = r_dict["account_head"]
    pat_str = r_dict.get("pattern")
    direction = r_dict.get("direction", "ANY").upper()
    conf = float(r_dict.get("confidence", 0.90))
    min_dr = float(r_dict["min_dr"]) if "min_dr" in r_dict else None
    max_dr = float(r_dict["max_dr"]) if "max_dr" in r_dict else None
    exact_dr = float(r_dict["exact_dr"]) if "exact_dr" in r_dict else None
    exclude_exact_dr = (
        float(r_dict["exclude_exact_dr"]) if "exclude_exact_dr" in r_dict else None
    )
    dr_in = [float(x) for x in r_dict["dr_in"]] if "dr_in" in r_dict else None

    exclude_pat_str = r_dict.get("exclude_pattern")
    patterns_all_str = r_dict.get("patterns_all")

    pattern = re.compile(pat_str, re.IGNORECASE) if pat_str else None
    exclude_pattern = (
        re.compile(exclude_pat_str, re.IGNORECASE) if exclude_pat_str else None
    )
    patterns_all = (
        [re.compile(p, re.IGNORECASE) for p in patterns_all_str]
        if patterns_all_str
        else None
    )

    def match_fn(p: str, dr: float, cr: float) -> bool:
        if direction == "DR" and dr <= 0:
            return False
        if direction == "CR" and cr <= 0:
            return False
        if min_dr is not None and dr < min_dr:
            return False
        if max_dr is not None and dr > max_dr:
            return False
        if exact_dr is not None and abs(dr - exact_dr) > 0.01:
            return False
        if exclude_exact_dr is not None and abs(dr - exclude_exact_dr) < 0.01:
            return False
        if dr_in is not None and not any(abs(dr - amt) < 0.01 for amt in dr_in):
            return False
        if exclude_pattern and exclude_pattern.search(p):
            return False
        if patterns_all and not all(pat.search(p) for pat in patterns_all):
            return False
        if pattern and not pattern.search(p):
            return False
        return True

    return (label, head, match_fn, conf)


RULES_COMMON: list[tuple] = [
    _compile_declarative_rule(r) for r in get_declarative_common_rules()
]
