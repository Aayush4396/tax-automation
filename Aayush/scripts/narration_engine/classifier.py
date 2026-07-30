# -*- coding: utf-8 -*-
"""
classifier.py
=============
Core classification engine.

classify(particulars, dr, cr, bank_key) → (label, account_head, confidence)

Rule chain per call:
  1. Bank-specific rules  (from rules_<bank>.py)
  2. Common cross-bank rules  (from rules_common.py)
  3. Merchant UPI detection   (from merchants.py)
     — only injected if the particulars contain a UPI pattern AND
       no specific rule has already fired
  4. Fallback: ("What is this?", "Suspense", 0.0)
"""

from __future__ import annotations
import importlib
import re
import pandas as pd

from narration_engine.merchants  import detect_merchant
from narration_engine.rules_common import RULES_COMMON

# Cache of already-imported bank rule lists
_RULES_CACHE: dict[str, list[tuple]] = {}

# Pattern that marks a transaction as UPI (for merchant detection step)
_UPI_PAT = re.compile(
    r"\bUPI[/ -]|UPIOUT/|UPI\s*IN/|UPI/DR/|UPI/CR/|^UPI/",
    re.IGNORECASE,
)


def _get_bank_rules(bank_key: str) -> list[tuple]:
    """Lazily import and cache the rules list for a given bank key."""
    if bank_key in _RULES_CACHE:
        return _RULES_CACHE[bank_key]

    module_name = f"narration_engine.rules_{bank_key}"
    attr_name   = f"RULES_{bank_key.upper()}"
    try:
        mod   = importlib.import_module(module_name)
        rules = getattr(mod, attr_name, [])
    except (ImportError, AttributeError):
        rules = []

    _RULES_CACHE[bank_key] = rules
    return rules


def _classify_raw(particulars: str,
                  dr: float,
                  cr: float,
                  bank_key: str = "unknown") -> tuple[str, str, float]:
    """
    Classify a single transaction without overrides.
    """
    # Clean up newlines, especially when they split words (e.g., "INTERES\n T" or "RE\n FUND")
    raw_p = str(particulars)
    healed = re.sub(r'(?<=[a-zA-Z])\s*\n\s*(?=[a-zA-Z])', '', raw_p)
    healed = re.sub(r'\s*\n\s*', ' ', healed)
    p = re.sub(r'\s+', ' ', healed).strip()
    dr = float(dr) if pd.notna(dr) else 0.0
    cr = float(cr) if pd.notna(cr) else 0.0

    # ── Step 1: Bank-specific rules ────────────────────────────────────────
    for label, head, fn, conf in _get_bank_rules(bank_key):
        try:
            if fn(p, dr, cr):
                return label, head, conf
        except Exception:
            continue

    # ── Step 2: Common rules (stop before UPI generics + fallback) ─────────
    # We exclude the last 3 rules (UPI Payment, UPI Receipt, What is this?) so
    # merchant detection runs BEFORE the generic UPI Payment/Receipt catch-all.
    for rule in RULES_COMMON[:-3]:
        label, head, fn, conf = rule
        try:
            if fn(p, dr, cr):
                return label, head, conf
        except Exception:
            continue

    # ── Step 3: Merchant UPI detection ────────────────────────────────────
    if _UPI_PAT.search(p):
        result = detect_merchant(p)
        if result:
            label, head, conf = result
            return label, head, conf

    # ── Step 4: Generic UPI Payment / Receipt (after merchant detection) ───
    for rule in RULES_COMMON[-3:-1]:      # UPI Payment + UPI Receipt (not fallback)
        label, head, fn, conf = rule
        try:
            if fn(p, dr, cr):
                return label, head, conf
        except Exception:
            continue

    # ── Step 5: Fallback ───────────────────────────────────────────────────
    return "What is this?", "Suspense", 0.0


def classify(particulars: str,
             dr: float,
             cr: float,
             bank_key: str = "unknown") -> tuple[str, str, float]:
    """
    Classify a single transaction, applying any global overrides.
    """
    label, head, conf = _classify_raw(particulars, dr, cr, bank_key)

    # Override: CRED payments of 500 or below are personal spending, not credit card payments
    if head == "Credit Card" and 0 < dr <= 500:
        head = "Personal"
        if label == "Credit Card Bill Payment (CRED)":
            label = "UPI - CRED"

    return label, head, conf
