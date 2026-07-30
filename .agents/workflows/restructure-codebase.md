---
description: Orchestrates the migration of legacy duplicated entity scripts into a centralized, config-driven Python package (`tax_automation`).
---

# Workflow: Restructure Tax Codebase

Orchestrates the migration of legacy duplicated entity scripts into a centralized, config-driven Python package (`tax_automation`).

---

## Overview

This workflow transforms duplicated scripts across `Aayush/`, `Ajay/`, and `Sunita/` into a single, modular Python package. It externalizes account IDs, display names, UPI refs, landlord VPAs, family member names, passwords, and sheet skip lists into JSON configuration files and `.env` credentials.

**Command**: `/restructure-codebase`

---

## Execution Steps

### Step 1: Externalize Configurations & Secrets
1. Create `config/entities/aayush.json`, `config/entities/ajay.json`, and `config/entities/sunita.json`.
2. Move account IDs, display names, signals, self-transfer UPI refs, rent VPAs, family member lists, and sheet skip lists into entity JSON files.
3. Create `config/consolidation/<entity>_<fy>.json` files for statement consolidation mappings.
4. Create `.env.example` and move PDF/Excel passwords to `.env`.

### Step 2: Establish Package Architecture
1. Create `src/tax_automation/` package structure with `__init__.py` files.
2. Build `config_loader.py` to parse JSON configurations and `.env` credentials dynamically.
3. Move identical engine files (`auto_header.py`, `classifier.py`, `merchants.py`, `parse_cc.py`, `cc_category_map.py`) into `src/tax_automation/core/`.
4. Merge `exporter.py` (using Aayush version as superset with `assign_pivot_categories`) into `src/tax_automation/exporters/`.

### Step 3: Modularize Classification Rules
1. Diff `rules_common.py` across folders: move base rules to `src/tax_automation/rules/common_base.py`, move Ajay deltas (~15KB) to `rules/entity_extensions/ajay_rules.py`.
2. Diff bank rule files (`rules_hdfc.py`, `rules_sbi.py`, `rules_kotak.py`): extract base rules to `rules/banks/` and entity-specific additions to `rules/entity_extensions/`.
3. Create `rules/loader.py` to assemble runtime rule chains (`entity_extensions + bank_base + common_base`).

### Step 4: Generalize CLI & Diagnostic Tools
1. Convert `run_narration.py` into unified CLI `src/tax_automation/cli.py`.
2. Move diagnostic scripts (`check_contras.py`, `check_narration_results.py`, `parse_narration_stats.py`, `parse_all_stats.py`) to `src/tax_automation/tools/` and update to use `config_loader`.
3. Move pipeline runners (`run_and_verify.ps1`, `run_and_verify.sh`) to `scripts/` and parameterize with `--entity`.

### Step 5: Validate Output Parity & Human Gate
1. Run narration engine for Aayush, Ajay, and Sunita on existing datasets using both legacy and refactored packages.
2. Diff generated Excel ledgers to verify 100% row count, confidence score, and narration text parity.
3. **Approval Gate**: Present parity report to user before removing legacy script directories.
