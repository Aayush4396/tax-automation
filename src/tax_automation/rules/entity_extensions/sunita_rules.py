# -*- coding: utf-8 -*-
"""
sunita_rules.py
===============
Entity-specific classification rules for Sunita. Appended before bank base rules.
"""

from __future__ import annotations
import re

EXTRA_RULES: dict[str, list[tuple]] = {
    "common": [],
    "hdfc": [],
    "kotak": [],
    "sbi": [],
}
