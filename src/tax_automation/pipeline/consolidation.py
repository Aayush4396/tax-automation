# -*- coding: utf-8 -*-
"""consolidation.py.

Bank statement consolidation module.
Handles consolidation of raw bank statements into a canonical multi-sheet Excel file.
"""

from __future__ import annotations
from pathlib import Path

from tax_automation.config_loader import (
    get_entity_config,
    resolve_input_dir,
    resolve_output_dir,
)
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
    config = get_entity_config(entity_id)
    entity_name = config.get("display_name", entity_id.title())

    if input_dir is None:
        input_dir = resolve_input_dir(entity_id, fy, "bank_statements")

    if output_dir is None:
        output_dir = resolve_output_dir(entity_id, fy)

    output_path = consolidate_entity_statements(
        entity_id, fy, data_dir=input_dir, output_dir=output_dir
    )

    print(
        f"[OK] Consolidated statements for {entity_name} ({fy}) "
        f"saved to {output_path}"
    )
    return output_path
