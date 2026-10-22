# -*- coding: utf-8 -*-
"""Pydantic schemas for diagnostics endpoints."""

from __future__ import annotations
from pydantic import BaseModel


class ContraResult(BaseModel):
    entity_id: str
    fy: str
    total_contras: int
    total_debit: float
    total_credit: float
    difference: float
    balanced: bool
    message: str


class ConfidenceBand(BaseModel):
    count: int
    pct: float


class NarrationStatsResponse(BaseModel):
    entity_id: str
    fy: str
    total: int
    high_confidence: ConfidenceBand
    med_confidence: ConfidenceBand
    low_confidence: ConfidenceBand


class ResultsCheckResponse(BaseModel):
    entity_id: str
    fy: str
    total_sheets: int
    bank_sheets: int
    sheet_names: list[str]
    bank_sheet_names: list[str]


class BankSummaryResponse(BaseModel):
    entity_id: str
    fy: str
    rows: list[dict]
