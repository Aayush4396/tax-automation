# -*- coding: utf-8 -*-
"""Router: /pipeline — Consolidation and narration processing."""

from __future__ import annotations
from pathlib import Path

from fastapi import APIRouter, HTTPException, status

from tax_automation.api.deps import validate_entity_fy
from tax_automation.api.schemas.pipeline import (
    ConsolidateResponse,
    ProcessResponse,
    RunAllResponse,
    PipelineRunRequest,
)
from tax_automation.pipeline.consolidation import consolidate_entity
from tax_automation.pipeline.narration import process_entity_narration

router = APIRouter(prefix="/pipeline", tags=["Pipeline"])


# ---------------------------------------------------------------------------
# POST /pipeline/{entity_id}/{fy}/consolidate
# ---------------------------------------------------------------------------
@router.post(
    "/{entity_id}/{fy}/consolidate",
    summary="Consolidate raw bank statements",
    response_model=ConsolidateResponse,
)
def run_consolidate(entity_id: str, fy: str) -> ConsolidateResponse:
    """Reads all raw statement files from the consolidation map and merges them
    into a single multi-sheet workbook at
    `data/{entity}/{FY}/output/consolidated_statements.xlsx`.
    """
    eid, f = validate_entity_fy(entity_id, fy)
    try:
        output_path = consolidate_entity(eid, f)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Consolidation failed: {exc}",
        )

    return ConsolidateResponse(
        entity_id=eid,
        fy=f,
        status="success",
        output_path=str(output_path),
        message=f"Consolidated statements saved to {output_path.name}",
    )


# ---------------------------------------------------------------------------
# POST /pipeline/{entity_id}/{fy}/process
# ---------------------------------------------------------------------------
@router.post(
    "/{entity_id}/{fy}/process",
    summary="Run narration pipeline (classify transactions, generate ledger)",
    response_model=ProcessResponse,
)
def run_process(
    entity_id: str,
    fy: str,
    body: PipelineRunRequest = PipelineRunRequest(),
) -> ProcessResponse:
    """Loads the consolidated workbook, classifies every transaction using the
    entity's full rule chain, and writes the narrated Excel ledger.

    Optionally accepts `input_path` and `output_path` overrides in the request body.
    """
    eid, f = validate_entity_fy(entity_id, fy)

    in_p = Path(body.input_path) if body.input_path else None
    out_p = Path(body.output_path) if body.output_path else None

    try:
        output_path = process_entity_narration(eid, f, in_p, out_p)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Processing failed: {exc}",
        )

    return ProcessResponse(
        entity_id=eid,
        fy=f,
        status="success",
        output_path=str(output_path),
        message=f"Narrated ledger saved to {output_path.name}",
    )


# ---------------------------------------------------------------------------
# POST /pipeline/{entity_id}/{fy}/run-all
# ---------------------------------------------------------------------------
@router.post(
    "/{entity_id}/{fy}/run-all",
    summary="Consolidate + Process in one shot",
    response_model=RunAllResponse,
)
def run_all(entity_id: str, fy: str) -> RunAllResponse:
    """Runs consolidation followed immediately by narration processing."""
    eid, f = validate_entity_fy(entity_id, fy)

    # Step 1: Consolidate
    try:
        conso_path = consolidate_entity(eid, f)
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Consolidation: {exc}"
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Consolidation failed: {exc}",
        )

    conso_resp = ConsolidateResponse(
        entity_id=eid,
        fy=f,
        status="success",
        output_path=str(conso_path),
        message=f"Consolidated statements saved to {conso_path.name}",
    )

    # Step 2: Process
    try:
        narr_path = process_entity_narration(eid, f)
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Processing: {exc}"
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Processing failed: {exc}",
        )

    narr_resp = ProcessResponse(
        entity_id=eid,
        fy=f,
        status="success",
        output_path=str(narr_path),
        message=f"Narrated ledger saved to {narr_path.name}",
    )

    return RunAllResponse(
        entity_id=eid,
        fy=f,
        consolidate=conso_resp,
        process=narr_resp,
    )
