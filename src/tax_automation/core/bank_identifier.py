# -*- coding: utf-8 -*-
"""
bank_identifier.py
==================
Scores a sheet's content against bank registry configurations and returns
the best-matching bank key + match score.

Scoring model:
  meta_score   = fraction of bank's meta_signals found (case-insensitive)
                 anywhere in the metadata text (rows above the header row)
  header_score = fraction of bank's header_signals found in the header row columns
  final_score  = meta_weight * meta_score + header_weight * header_score

All numeric thresholds are loaded from config/scoring.json so they can be
tuned without editing Python code.
"""

from __future__ import annotations

from tax_automation.config_loader import get_scoring_config

_scoring = get_scoring_config().get("bank_identification", {})

# Weights — configurable via config/scoring.json
_META_WEIGHT: float = float(_scoring.get("meta_weight", 0.60))
_HEADER_WEIGHT: float = float(_scoring.get("header_weight", 0.40))
_MIN_THRESHOLD: float = float(_scoring.get("min_threshold", 0.55))
_BOOST_MIN_HEADER: float = float(_scoring.get("header_boost_min_header_score", 0.80))
_BOOST_MIN_META: float = float(_scoring.get("header_boost_min_meta_score", 0.20))
_BOOST_FLOOR: float = float(_scoring.get("header_boost_floor", 0.70))


def identify_bank(
    sheet_rows: list[tuple],
    header_row_idx: int,
    bank_registry: dict[str, dict],
    sheet_name: str = "",
) -> tuple[str, float]:
    """
    Parameters
    ----------
    sheet_rows     : all rows from the sheet (list of tuples, openpyxl values_only)
    header_row_idx : 0-based index of the detected header row
    bank_registry  : dictionary of bank configurations loaded from JSON profile
    sheet_name     : name of the sheet in the workbook

    Returns
    -------
    (bank_key, score)  — bank_key is "unknown" if score < _MIN_THRESHOLD
    """
    # Build a flat string from all metadata rows (before header)
    meta_text = " ".join(
        str(c).strip()
        for row in sheet_rows[:header_row_idx]
        for c in row
        if c is not None and str(c).strip() not in ("", "nan", "none")
    ).lower()

    meta_text += " " + sheet_name.lower()

    # Build a set of header column names (lowercased, stripped)
    if header_row_idx < len(sheet_rows):
        header_row = sheet_rows[header_row_idx]
        header_cols = {
            str(c).strip().lower()
            for c in header_row
            if c is not None and str(c).strip() not in ("", "nan", "none")
        }
    else:
        header_cols = set()

    # Check if there are non-empty metadata rows above the header
    has_preamble = any(
        c
        for row in sheet_rows[:header_row_idx]
        for c in row
        if c is not None and str(c).strip() not in ("", "nan", "none")
    )

    best_key = "unknown"
    best_score = 0.0

    for bank_key, cfg in bank_registry.items():
        # ── meta score ──────────────────────────────────────────────────
        meta_sigs = cfg.get("meta_signals", [])
        if meta_sigs:
            meta_hits = sum(1 for sig in meta_sigs if sig.lower() in meta_text)
            meta_score = meta_hits / len(meta_sigs)
        else:
            meta_score = 0.0

        # ── header score ────────────────────────────────────────────────
        hdr_sigs = cfg.get("header_signals", [])
        if hdr_sigs:
            hdr_hits = sum(
                1
                for sig in hdr_sigs
                if sig.strip().lower() in header_cols
                or any(sig.strip().lower() in col for col in header_cols)
            )
            header_score = hdr_hits / len(hdr_sigs)
        else:
            header_score = 0.0

        if not has_preamble:
            # Statements starting directly at header (CSVs, clean Excel)
            # rely on header score
            final_score = header_score if header_score > 0 else meta_score
        else:
            final_score = _META_WEIGHT * meta_score + _HEADER_WEIGHT * header_score
            # If headers are a strong match, ensure a minimum confidence floor
            if header_score >= _BOOST_MIN_HEADER and meta_score >= _BOOST_MIN_META:
                final_score = max(final_score, _BOOST_FLOOR)

        if final_score > best_score:
            best_score = final_score
            best_key = bank_key

    if best_score < _MIN_THRESHOLD:
        return "unknown", best_score

    return best_key, round(best_score, 3)
