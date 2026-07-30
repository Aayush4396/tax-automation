---
description: Guides the onboarding of a new entity/person by generating JSON configs and directory structures without editing source code.
---

# Workflow: Add New Entity Profile

Guides the user through onboarding a new entity/person (e.g. `archit` or a new family member) into the tax automation system without modifying core source code.

---

## Overview

Sets up JSON profile configurations, data directory structure, and consolidation mappings for a new entity.

**Command**: `/add-new-entity`

---

## Execution Steps

### Step 1: Entity Config Specification
1. Prompt for new **Entity ID** (e.g. `archit`) and **Display Name** (e.g. `Archit Gupta`).
2. Collect bank account details (Bank Name, Account ID, Last 4 digits).
3. Collect family member names for self-transfer filtering.
4. Collect self-transfer UPI reference numbers and landlord VPAs (if any).

### Step 2: Generate JSON Configuration Files
1. Create `config/entities/<entity_id>.json` populated with collected metadata and bank registry signals.
2. Create initial `config/consolidation/<entity_id>_fy26.json` for mapping raw bank files to workbook sheets.
3. If statement PDFs/Excels are password protected, add keys to `.env` file.

### Step 3: Setup Data Directory Layout
1. Create data directory tree:
   ```text
   data/<entity_id>/
   ├── Data/FY26/Bank_Statements/
   └── Generated Data/FY26/
   ```

### Step 4: Verification Test
1. Place a sample statement in `data/<entity_id>/Data/FY26/Bank_Statements/`.
2. Run `/process-entity-taxes` for the new entity.
3. Inspect generated ledger to confirm proper bank identification, classification, and formatting.
