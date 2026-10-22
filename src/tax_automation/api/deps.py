# -*- coding: utf-8 -*-
"""Shared FastAPI dependencies and utility resolvers."""

from __future__ import annotations
from pathlib import Path
from fastapi import HTTPException

from tax_automation.config_loader import resolve_output_dir


def get_ledger_path(entity_id: str, fy: str) -> Path:
    """Resolves the canonical narrated_ledger path, raising 404 if not found."""
    canonical = resolve_output_dir(entity_id, fy) / "narrated_ledger.xlsx"
    if canonical.exists():
        return canonical

    raise HTTPException(
        status_code=404,
        detail=f"Narrated ledger not found for {entity_id} {fy}. "
        "Run POST /pipeline/{entity_id}/{fy}/process first.",
    )


def get_consolidated_path(entity_id: str, fy: str) -> Path:
    """Resolves the consolidated_statements path, raising 404 if not found."""
    path = resolve_output_dir(entity_id, fy) / "consolidated_statements.xlsx"
    if not path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Consolidated statements not found for {entity_id} {fy}. "
            "Run POST /pipeline/{entity_id}/{fy}/consolidate first.",
        )
    return path


def validate_entity_fy(entity_id: str, fy: str) -> tuple[str, str]:
    """Normalises and validates entity_id and fy path params."""
    eid = entity_id.strip().lower()
    f = fy.strip().upper()
    if not eid:
        raise HTTPException(status_code=422, detail="entity_id cannot be empty")
    if not f.startswith("FY"):
        raise HTTPException(
            status_code=422, detail="fy must start with 'FY', e.g. FY26"
        )
    return eid, f
