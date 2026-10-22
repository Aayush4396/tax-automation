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
1. Read profile `accounts` and bank registry from `config/entities/<entity>.json`.
2. Scan generated ledger at `data/<entity>/<FY>/output/narrated_ledger.xlsx`.
3. Extract all transactions tagged as `Contra - <Bank>` across worksheets.
4. Verify that every debit transfer from Account A has a matching credit transfer in Account B.
5. Report asymmetric or missing contra entries:
   ```bash
   curl "http://localhost:8000/diagnostics/<entity>/<FY>/contras"
   ```

### Step 2: Confidence Score Analysis (`parse_narration_stats.py`)
1. Scan generated ledger `data/<entity>/<FY>/output/narrated_ledger.xlsx`.
2. Exclude summary sheets specified in entity configuration (`output_sheet_names`).
3. Calculate percentage of transactions classified across high, medium, and low confidence tiers:
   ```bash
   # Via REST API:
   curl "http://localhost:8000/diagnostics/<entity>/<FY>/narration-stats"
   ```

### Step 3: Performance & Summary Analytics (`parse_all_stats.py`)
1. Extract bank opening & closing balances from `Bank Summary` worksheet.
2. Aggregate category debit/credit totals:
   ```bash
   # Via REST API:
   curl "http://localhost:8000/diagnostics/<entity>/<FY>/bank-summary"
   ```
