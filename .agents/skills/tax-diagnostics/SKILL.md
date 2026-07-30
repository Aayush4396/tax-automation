---
name: tax-diagnostics
description: Diagnostic toolsuite for verifying contras, analyzing classification confidence scores, calculating human narration match rates, and inspecting bank pivots.
---

# Tax Diagnostics Skill

## Objective
Execute validation checks on narrated Excel ledgers to ensure 100% classification integrity, contra symmetry, and high confidence scores.

---

## Execution Steps

### Step 1: Contra Symmetry Verification (`check_contras.py`)
1. Read profile `BANK_REGISTRY` from `config/entities/<entity>.json`.
2. Extract all transactions tagged as `Contra - <Bank>` across worksheets.
3. Verify that every debit transfer from Account A has a matching credit transfer in Account B (matching date and amount).
4. Report asymmetric or missing contra entries.

### Step 2: Confidence Score Analysis (`check_narration_results.py`)
1. Scan generated ledger `data/<entity>/Generated Data/<FY>/<Entity>_Consolidated_Bank_Ledger_<FY>.xlsx`.
2. Exclude summary sheets specified in entity configuration (`output_sheet_names`).
3. Identify transactions with confidence score `< 0.70`.
4. Calculate percentage of transactions classified with high confidence (`≥ 0.85`).

### Step 3: Performance & Summary Analytics (`parse_all_stats.py`)
1. Extract bank opening & closing balances from `Bank Summary` worksheet.
2. Aggregate category debit/credit totals.
3. Output summary report to console/log.
