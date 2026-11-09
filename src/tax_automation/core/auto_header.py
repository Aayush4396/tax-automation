# -*- coding: utf-8 -*-
"""
auto_header.py
==============
Scans top N rows of a statement worksheet to dynamically locate the header row.
Keyword lists and the scan limit are loaded from config/header_keywords.json.
"""

from __future__ import annotations

from tax_automation.config_loader import get_header_keywords_config

_cfg = get_header_keywords_config()

_DEFAULT_DATE_KEYS = {
    "date",
    "txn date",
    "tran date",
    "transaction date",
    "value date",
    "value dt",
    "srl no",
    "sl. no.",
    "sl no",
}
_DEFAULT_AMT_KEYS = {
    "debit",
    "credit",
    "withdrawal",
    "deposit",
    "dr",
    "cr",
    "amount",
    "balance",
    "withdrawals",
    "deposits",
    "withdrawal amt",
    "withdrawal amt.",
    "deposit amt",
    "deposit amt.",
    "closing balance",
}

# Use config values when present; fall back to in-code defaults.
# Defensive: handle null values in the JSON (e.g. "date_keywords": null).
_raw_date = _cfg.get("date_keywords") or []
_raw_amt = _cfg.get("amount_keywords") or []
_DATE_KEYS = set(_raw_date) if _raw_date else _DEFAULT_DATE_KEYS
_AMT_KEYS = set(_raw_amt) if _raw_amt else _DEFAULT_AMT_KEYS

# Max rows to scan for the header — configurable per deployment
_MAX_SCAN_ROWS: int = int(_cfg.get("max_scan_rows", 40))


def find_header_row(rows: list, max_scan: int | None = None) -> int:
    """Finds header row index by scanning first max_scan rows.

    ``max_scan`` defaults to the value in ``config/header_keywords.json``
    (key ``max_scan_rows``, default 40) so callers that don't pass the
    argument automatically pick up any tuned value from config.
    """
    if max_scan is None:
        max_scan = _MAX_SCAN_ROWS

    best_idx = 0
    best_score = -1

    for idx, row in enumerate(rows[:max_scan]):
        if not row:
            continue
        cells = [str(c).strip().lower() for c in row if c is not None]
        if not cells:
            continue

        score = 0
        # Use config-driven keyword sets exclusively — no inline hardcoding.
        has_date = any(
            any(dk in c for dk in _DATE_KEYS) or c in _DATE_KEYS for c in cells
        )
        has_amt = any(any(ak in c for ak in _AMT_KEYS) or c in _AMT_KEYS for c in cells)

        if has_date:
            score += 2
        if has_amt:
            score += 2

        score += len([c for c in cells if c])

        if score > best_score and (has_date or has_amt):
            best_score = score
            best_idx = idx

    return best_idx
