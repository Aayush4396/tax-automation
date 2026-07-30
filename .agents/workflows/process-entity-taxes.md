---
description: Consolidates bank statements, runs narration classification, exports Excel ledgers, and executes validation diagnostics for a profile & FY.
---

# Workflow: Process Entity Taxes

Automates end-to-end tax statement consolidation, narration classification, Excel ledger export, and diagnostic verification for a specified entity profile and Financial Year.

---

## Overview

Processes raw or multi-sheet bank statements for an entity (`aayush`, `ajay`, `sunita`, `archit`), applies the config-driven classification pipeline, generates formatted Excel workbooks, and runs validation diagnostics.

**Command**: `/process-entity-taxes`

---

## Execution Steps

### Step 1: Parameters Prompt & Context Setup
1. Prompt for target **Entity Profile** (`aayush`, `ajay`, `sunita`, `archit`).
2. Prompt for target **Financial Year** (`FY24`, `FY25`, `FY26`).
3. Load profile configuration from `config/entities/<entity>.json`.

### Step 2: Statement Consolidation
1. Check if individual bank statement files exist in `data/<entity>/Data/<FY>/Bank_Statements/`.
2. If raw statements exist, execute `/tax-report-consolidator` skill using `config/consolidation/<entity>_<fy>.json`.
3. Output consolidated workbook: `All Bank Statements <Entity> <FY>.xlsx`.

### Step 3: Narration Classification & Export
1. Execute `/tax-statement-processor` skill with selected entity profile and FY.
2. Build runtime classification rule chain (`entity_extensions + bank_base + common_base`).
3. Write per-bank worksheets, Tally sheet, Conso ledger, Bank Summary, and Monthly Pivot.
4. Output finalized Excel workbook: `<Entity>_Consolidated_Bank_Ledger_<FY>.xlsx`.

### Step 4: Diagnostics & Parity Verification
1. Execute `/tax-diagnostics` skill:
   - Run `check_contras.py` to verify self-transfer symmetry across accounts.
   - Run `check_narration_results.py` to verify confidence scores and match rates.
2. Display summary dashboard report for human review.
