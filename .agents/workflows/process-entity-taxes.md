---
description: Consolidates bank statements, runs narration classification, exports Excel ledgers, and executes validation diagnostics for a profile & FY.
---

# Workflow: Process Entity Taxes

Automates end-to-end tax statement consolidation, narration classification, Excel ledger export, and diagnostic verification for a specified entity profile and Financial Year.

---

## Overview

Processes raw or consolidated bank statements for an entity (e.g., `demo_entity`), applies the config-driven classification pipeline, generates formatted Excel workbooks, and runs validation diagnostics.

**Command**: `/process-entity-taxes`

---

## Execution Steps

### Step 1: Parameters & Profile Verification
1. Identify target **Entity Profile** (e.g., `<entity_id>`) and **Financial Year** (`FY24`, `FY25`, `FY26`).
2. Verify profile configuration in `config/entities/<entity>.json`.

### Step 2: Statement Consolidation
1. Check if raw individual bank statements exist in `data/<entity>/<FY>/input/bank_statements/`.
2. If raw statements exist, consolidate via:
   ```bash
   python -m tax_automation consolidate --entity <entity> --fy <FY>
   ```
3. Output consolidated workbook: `data/<entity>/<FY>/output/consolidated_statements.xlsx`.

### Step 3: Narration Classification & Master Ledger Generation
1. Execute the narration pipeline:
   ```bash
   python -m tax_automation process --entity <entity> --fy <FY>
   ```
2. The pipeline:
   - Dynamic compiler synthesizes personal Contras, Family transfers, Rent rules, and custom rules.
   - Bank-specific rules evaluate bank transactions.
   - Universal Indian merchant & banking rules classify retail/utility spends.
   - Master Excel ledger written to `data/<entity>/<FY>/output/narrated_ledger.xlsx`.

### Step 4: Diagnostics & Parity Verification
1. Run contra symmetry verification:
   ```bash
   python -m tax_automation.tools.check_contras --entity <entity> --fy <FY>
   ```
2. Run narration score inspection:
   ```bash
   python -m tax_automation.tools.check_narration_results --entity <entity> --fy <FY>
   ```
3. Verify that all debit/credit contras match and inspect transactions flagged with confidence `< 0.70`.
