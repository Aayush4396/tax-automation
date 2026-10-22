---
description: Guides the onboarding of a new entity/person by generating JSON configs and directory structures without editing source code.
---

# Workflow: Add New Entity Profile

Guides the user through onboarding a new entity/taxpayer into the tax automation system with zero code changes.

---

## Overview

Scaffolds the declarative JSON profile configuration, canonical data directory tree, and consolidation mappings for a new taxpayer.

**Command**: `/add-new-entity`

---

## Execution Steps

### Step 1: Automated Scaffolding via API
Create the entity via the FastAPI REST endpoint:
```bash
curl -X POST "http://localhost:8000/entities" \
  -H "Content-Type: application/json" \
  -d '{"entity_id": "<entity_id>", "display_name": "<Full Name>", "pan": "<PAN>", "fy": "FY26"}'
```
This automatically:
1. Generates `config/entities/<entity_id>.json` conforming to `config/schemas/entity.json`.
2. Creates the canonical input directory: `data/<entity_id>/<FY>/input/bank_statements/`.
3. Creates the canonical output directory: `data/<entity_id>/<FY>/output/`.

### Step 2: Configure Declared Bank Accounts
In `config/entities/<entity_id>.json`, add the bank accounts using standard bank keys (`hdfc`, `sbi`, `kotak`, `axis`, `boi`, `federal`, `sbm`, `icici`, `generic`):
```json
"accounts": [
  {
    "account_key": "hdfc",
    "bank": "hdfc",
    "account_id": "HDFC 1234",
    "sheet_name": "HDFC 1234",
    "display_name": "HDFC Bank",
    "meta_signals_extra": ["1234"]
  }
]
```

### Step 3: Configure Personal Signals
Declare family members, rent keywords/landlords, and custom rules in `config/entities/<entity_id>.json`.

### Step 4: Add Consolidation Map (if multiple raw statements)
Create `config/consolidation/<entity_id>_<fy>.json` mapping filenames to worksheet names.

### Step 5: Verification Run
1. Place bank statement files in `data/<entity_id>/<FY>/input/bank_statements/` (or via `POST /files/<entity_id>/<FY>/upload`).
2. Run one-shot consolidation and narration:
   ```bash
   curl -X POST "http://localhost:8000/pipeline/<entity_id>/<FY>/run-all"
   ```
   *Or via Python directly:*
   ```python
   from tax_automation.pipeline.consolidation import consolidate_entity
   from tax_automation.pipeline.narration import process_entity_narration

   consolidate_entity("<entity_id>", "<FY>")
   process_entity_narration("<entity_id>", "<FY>")
   ```
3. Verify contras via `GET http://localhost:8000/diagnostics/<entity_id>/<FY>/contras` and review generated master ledger in `data/<entity_id>/<FY>/output/narrated_ledger.xlsx`.
