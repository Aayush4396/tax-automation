# -*- coding: utf-8 -*-
"""
consolidation.py
==================

Bank statement consolidation module.

This module handles the consolidation of raw bank statements into a unified format.
It is decoupled from the CLI and can be used independently.
"""

from __future__ import annotations
from pathlib import Path

from tax_automation.config_loader import get_entity_config
from tax_automation.consolidators.generic_consolidator import (
    consolidate_entity_statements,
)

__all__ = ["consolidate_entity", "consolidate_entity_statements"]


def consolidate_entity(
    entity_id: str,
    fy: str,
    input_dir: Path | None = None,
    output_dir: Path | None = None,
) -> Path:
    """Consolidate bank statements for a specific entity and financial year.

    Args:
        entity_id: Entity identifier (e.g., 'aayush')
        fy: Financial year (e.g., 'FY26')
        input_dir: Optional directory to search for input files
        output_dir: Optional directory for output files

    Returns:
        Path to the consolidated output file
    """
    # Load entity configuration
    config = get_entity_config(entity_id)
    entity_name = config.get("display_name", entity_id.title())
    entity_dir_name = entity_id.title()

    # Default input directory
    if input_dir is None:
        input_dir = Path("data") / entity_dir_name / "Bank Statements" / fy
    input_dir.mkdir(parents=True, exist_ok=True)

    # Default output directory
    if output_dir is None:
        output_dir = Path("data") / entity_dir_name / "Generated Data" / fy
    output_dir.mkdir(parents=True, exist_ok=True)

    # Perform consolidation using existing consolidator
    output_path = consolidate_entity_statements(entity_id, fy)

    print(
        f"[OK] Consolidated statements for {entity_name} ({fy}) "
        f"saved to {output_path}"
    )
    return output_path
