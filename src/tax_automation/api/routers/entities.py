# -*- coding: utf-8 -*-
"""Router: /entities — Entity profile management."""

from __future__ import annotations
import json
import re
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, status

from tax_automation.config_loader import (
    CONFIG_DIR,
    get_entity_config,
    resolve_input_dir,
    resolve_output_dir,
)
from tax_automation.api.schemas.entity import (
    CreateEntityRequest,
    EntityResponse,
    UpdateEntityRequest,
)

router = APIRouter(prefix="/entities", tags=["Entities"])

_ENTITIES_DIR: Path = CONFIG_DIR / "entities"


def _list_entity_ids() -> list[str]:
    """Returns all configured entity IDs from the entities config directory."""
    if not _ENTITIES_DIR.exists():
        return []
    return sorted(f.stem for f in _ENTITIES_DIR.glob("*.json"))


def _load_entity(entity_id: str) -> dict[str, Any]:
    try:
        return get_entity_config(entity_id)
    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Entity '{entity_id}' not found. Available: {_list_entity_ids()}",
        )


# ---------------------------------------------------------------------------
# GET /entities
# ---------------------------------------------------------------------------
@router.get(
    "",
    summary="List all configured entity IDs",
    response_model=list[str],
)
def list_entities() -> list[str]:
    """Returns a list of all entity IDs that have a config file in config/entities/."""
    return _list_entity_ids()


# ---------------------------------------------------------------------------
# GET /entities/{entity_id}
# ---------------------------------------------------------------------------
@router.get(
    "/{entity_id}",
    summary="Get entity configuration",
    response_model=EntityResponse,
)
def get_entity(entity_id: str) -> EntityResponse:
    """Returns the full JSON configuration for a single entity."""
    cfg = _load_entity(entity_id.lower())
    return EntityResponse(**{k: v for k, v in cfg.items() if k != "$schema"})


# ---------------------------------------------------------------------------
# POST /entities
# ---------------------------------------------------------------------------
@router.post(
    "",
    summary="Create (init) a new entity",
    status_code=status.HTTP_201_CREATED,
    response_model=EntityResponse,
)
def create_entity(body: CreateEntityRequest) -> EntityResponse:
    """Scaffolds a new entity config file and data directories."""
    eid = body.entity_id.strip().lower()
    if not re.match(r"^[a-z0-9_]+$", eid):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="entity_id must be lowercase alphanumeric or underscore",
        )

    _ENTITIES_DIR.mkdir(parents=True, exist_ok=True)
    cfg_path = _ENTITIES_DIR / f"{eid}.json"

    if cfg_path.exists():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Entity '{eid}' already exists. "
            f"Use PATCH /entities/{eid} to update.",
        )

    norm_name = re.sub(r"\s+", r"\\s*", body.display_name.upper())
    profile_data: dict[str, Any] = {
        "$schema": "../schemas/entity.json",
        "entity_id": eid,
        "display_name": body.display_name,
        "pan": body.pan or "",
        "self_patterns": [norm_name],
        "self_vpas": [],
        "family_members": [],
        "rent": {"landlords": [], "vpas": [], "keywords": []},
        "custom_rules": [],
        "output_sheet_names": [
            "For Tally",
            "Conso",
            "Bank Summary",
            "Monthly Pivot",
            "Guidelines",
        ],
        "accounts": [],
    }

    with open(cfg_path, "w", encoding="utf-8") as f:
        json.dump(profile_data, f, indent=2)

    # Scaffold input/output directories
    resolve_input_dir(eid, body.fy, "bank_statements").mkdir(
        parents=True, exist_ok=True
    )
    resolve_output_dir(eid, body.fy).mkdir(parents=True, exist_ok=True)

    return EntityResponse(**{k: v for k, v in profile_data.items() if k != "$schema"})


# ---------------------------------------------------------------------------
# PATCH /entities/{entity_id}
# ---------------------------------------------------------------------------
@router.patch(
    "/{entity_id}",
    summary="Update entity configuration",
    response_model=EntityResponse,
)
def update_entity(entity_id: str, body: UpdateEntityRequest) -> EntityResponse:
    """Merges the supplied fields into the existing entity config and saves it."""
    eid = entity_id.lower()
    cfg = _load_entity(eid)

    update_data = body.model_dump(exclude_none=True)
    for key, value in update_data.items():
        if isinstance(value, list) and key in cfg and isinstance(cfg[key], list):
            cfg[key] = value
        elif isinstance(value, dict) and key in cfg and isinstance(cfg[key], dict):
            cfg[key].update(value)
        else:
            cfg[key] = value

    cfg_path = _ENTITIES_DIR / f"{eid}.json"
    with open(cfg_path, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)

    return EntityResponse(**{k: v for k, v in cfg.items() if k != "$schema"})
