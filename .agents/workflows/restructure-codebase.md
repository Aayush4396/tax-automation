---
description: Orchestrates the migration of legacy duplicated entity scripts into a centralized, config-driven Python package (`tax_automation`).
---

# Workflow: Restructure Tax Codebase

Orchestrates the architecture migration of legacy duplicated entity scripts into a centralized, plug-and-play Python package (`tax_automation`).

---

## Overview

Transforms duplicated scripts across legacy entity roots into a single modular Python package. Externalizes all entity specifics (family members, UPI VPAs, rent landlords, phone numbers, FnF amounts) into declarative JSON configurations (`config/entities/<entity>.json`). Eliminates all hardcodings, `sys.path` hacks, and enforces standardized imports and directory layouts.

**Command**: `/restructure-codebase`

---

## Execution Phases

### Phase 1: Package Structure & Reusable Bank Schemas
- Initialize package `__init__.py` files across all subpackages.
- Extract 10 reusable bank schemas into `config/banks/` (`hdfc.json`, `sbi.json`, `kotak.json`, `axis.json`, `boi.json`, `federal.json`, `sbm.json`, `huf.json`, `icici.json`, `generic.json`).

### Phase 2: Purge Hardcodings from Rules & Bank Base Modules
- Cleanse `config/rules_common.json` of family members, landlord names, phone numbers, and contra rules. Retain purely universal Indian banking/merchant rules.
- Cleanse `src/tax_automation/rules/banks/` of entity-specific rules.

### Phase 3: Core Plumbing & Dynamic Rule Compiler
- Implement dynamic rule compiler in `src/tax_automation/rules/loader.py` that dynamically synthesizes Contras, Family transfers, Rent rules, and custom rules from entity JSON configs.
- Update `config_loader.py` with `get_bank_schema()` and `resolve_entity_bank_registry()`.

### Phase 4: Pipelines, Exporters & Diagnostic Tools
- Standardize all file resolution on `resolve_input_dir()` and `resolve_output_dir()`.
- Eliminate legacy output file paths and duplicated writes.
- Update `exporter.py` and diagnostic tools.

### Phase 5: Declarative Entity Profiles & Onboarding CLI
- Update `config/schemas/entity.json` schema.
- Migrate entity JSON profiles (`config/entities/*.json`) to the declarative schema.
- Add `init-entity` command to `src/tax_automation/cli.py`.

### Phase 6: Lossless Data Migration & Privacy Protection
- Migrate historical statements losslessly into `data/<entity>/<FY>/input/`.
- Update `.gitignore` so real financial statements are never tracked in Git, while `.gitkeep` files preserve directory structure.

### Phase 7: Purge Legacy Scripts
- Safely delete legacy un-modular entity directories and deprecated scripts.
- Verify zero regression with test suite and flake8.

### Phase 8: Documentation & Workflow Sync
- Update workflows, skills, and root `README.md` to reflect unified architecture.
