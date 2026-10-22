# -*- coding: utf-8 -*-
"""Router: /files — File upload and download for statements and ledgers."""

from __future__ import annotations
import shutil
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile, File, status
from fastapi.responses import FileResponse

from tax_automation.api.deps import (
    get_ledger_path,
    get_consolidated_path,
    validate_entity_fy,
)
from tax_automation.config_loader import resolve_input_dir

router = APIRouter(prefix="/files", tags=["Files"])

# Allowed upload extensions
_ALLOWED_EXTS = {".xlsx", ".xls", ".csv", ".pdf"}


# ---------------------------------------------------------------------------
# GET /files/{entity_id}/{fy}/ledger
# ---------------------------------------------------------------------------
@router.get(
    "/{entity_id}/{fy}/ledger",
    summary="Download the narrated ledger Excel file",
    response_class=FileResponse,
)
def download_ledger(entity_id: str, fy: str) -> FileResponse:
    """Streams the `narrated_ledger.xlsx` for the given entity and FY."""
    eid, f = validate_entity_fy(entity_id, fy)
    ledger = get_ledger_path(eid, f)
    filename = f"{eid}_{f}_narrated_ledger.xlsx"
    return FileResponse(
        path=str(ledger),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=filename,
    )


# ---------------------------------------------------------------------------
# GET /files/{entity_id}/{fy}/consolidated
# ---------------------------------------------------------------------------
@router.get(
    "/{entity_id}/{fy}/consolidated",
    summary="Download the consolidated statements Excel file",
    response_class=FileResponse,
)
def download_consolidated(entity_id: str, fy: str) -> FileResponse:
    """Streams the `consolidated_statements.xlsx` for the given entity and FY."""
    eid, f = validate_entity_fy(entity_id, fy)
    path = get_consolidated_path(eid, f)
    filename = f"{eid}_{f}_consolidated_statements.xlsx"
    return FileResponse(
        path=str(path),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=filename,
    )


# ---------------------------------------------------------------------------
# POST /files/{entity_id}/{fy}/upload
# ---------------------------------------------------------------------------
@router.post(
    "/{entity_id}/{fy}/upload",
    summary="Upload a raw bank statement file",
    status_code=status.HTTP_201_CREATED,
)
def upload_statement(
    entity_id: str,
    fy: str,
    file: UploadFile = File(
        ..., description="Bank statement file (xlsx, xls, csv, pdf)"
    ),
) -> dict:
    """Saves an uploaded bank statement to the canonical input directory:
    `data/{entity}/{FY}/input/bank_statements/`.

    After uploading, add the filename to `config/consolidation/{entity}_{fy}.json`
    and call `POST /pipeline/{entity_id}/{fy}/consolidate`.
    """
    eid, f = validate_entity_fy(entity_id, fy)

    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No filename provided",
        )

    ext = Path(file.filename).suffix.lower()
    if ext not in _ALLOWED_EXTS:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported file type '{ext}'. "
            f"Allowed: {', '.join(_ALLOWED_EXTS)}",
        )

    dest_dir = resolve_input_dir(eid, f, "bank_statements")
    dest_path = dest_dir / file.filename

    try:
        with open(dest_path, "wb") as out:
            shutil.copyfileobj(file.file, out)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save file: {exc}",
        )

    return {
        "status": "uploaded",
        "entity_id": eid,
        "fy": f,
        "filename": file.filename,
        "saved_to": str(dest_path),
        "next_step": f"POST /pipeline/{eid}/{f}/consolidate",
    }


# ---------------------------------------------------------------------------
# GET /files/{entity_id}/{fy}/list
# ---------------------------------------------------------------------------
@router.get(
    "/{entity_id}/{fy}/list",
    summary="List uploaded statement files for an entity/FY",
)
def list_uploaded_files(entity_id: str, fy: str) -> dict:
    """Returns all files currently in the input bank_statements directory."""
    eid, f = validate_entity_fy(entity_id, fy)
    input_dir = resolve_input_dir(eid, f, "bank_statements")

    if not input_dir.exists():
        return {"entity_id": eid, "fy": f, "files": []}

    files = [
        {
            "filename": p.name,
            "size_bytes": p.stat().st_size,
            "extension": p.suffix.lower(),
        }
        for p in sorted(input_dir.iterdir())
        if p.is_file() and not p.name.startswith(".")
    ]

    return {"entity_id": eid, "fy": f, "directory": str(input_dir), "files": files}
