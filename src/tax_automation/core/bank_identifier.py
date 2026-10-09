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
  final_score  = 0.60 * meta_score + 0.40 * header_score

Identification threshold: 0.55
"""

from __future__ import annotations

_META_WEIGHT = 0.60
_HEADER_WEIGHT = 0.40
_MIN_THRESHOLD = 0.55


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

        final_score = _META_WEIGHT * meta_score + _HEADER_WEIGHT * header_score

        if final_score > best_score:
            best_score = final_score
            best_key = bank_key

    if best_score < _MIN_THRESHOLD:
        return "unknown", best_score

    return best_key, round(best_score, 3)
