# -*- coding: utf-8 -*-
"""
auto_header.py
==============
Scans top N rows of a statement worksheet to dynamically locate the header row.
Keyword lists are loaded dynamically from config/header_keywords.json.
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

_DATE_KEYS = set(_cfg.get("date_keywords", [])) or _DEFAULT_DATE_KEYS
_AMT_KEYS = set(_cfg.get("amount_keywords", [])) or _DEFAULT_AMT_KEYS


def find_header_row(rows: list, max_scan: int = 40) -> int:
    """Finds header row index by scanning first max_scan rows."""
    best_idx = 0
    best_score = -1

    for idx, row in enumerate(rows[:max_scan]):
        if not row:
            continue
        cells = [str(c).strip().lower() for c in row if c is not None]
        if not cells:
            continue

        score = 0
        has_date = any(
            c in _DATE_KEYS or any(dk in c for dk in ("date", "txn date", "tran date"))
            for c in cells
        )
        has_amt = any(
            c in _AMT_KEYS
            or any(ak in c for ak in ("debit", "credit", "withdrawal", "deposit"))
            for c in cells
        )

        if has_date:
            score += 2
        if has_amt:
            score += 2

        score += len([c for c in cells if c])

        if score > best_score and (has_date or has_amt):
            best_score = score
            best_idx = idx

    return best_idx
