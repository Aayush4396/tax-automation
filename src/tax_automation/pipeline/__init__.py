# -*- coding: utf-8 -*-
"""Pipeline processing package for consolidation and narration."""

from tax_automation.pipeline.consolidation import consolidate_entity
from tax_automation.pipeline.narration import process_entity_narration

__all__ = ["consolidate_entity", "process_entity_narration"]
