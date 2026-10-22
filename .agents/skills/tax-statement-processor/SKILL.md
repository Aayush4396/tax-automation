---
name: tax-statement-processor
description: Config-driven processor for bank and credit card statements. Loads JSON profile configuration, builds dynamic rule chains, classifies transactions, and generates formatted Excel ledgers.
---

# Tax Statement Processor Skill

## Objective
Process bank statements and credit card statements for a designated entity profile (e.g., `<entity_id>`) and Financial Year (`FY24`, `FY25`, `FY26`).

---

## Execution Steps

### Step 1: Configuration & Profile Loading
1. Read profile JSON configuration from `config/entities/<entity>.json`.
2. Retrieve declared `accounts`, `family_members`, `rent`, and `custom_rules`.
3. Check for statement decryption keys in `.env` if files are password protected.

### Step 2: Dynamic Rule Chain Construction
1. Dynamic compiler in `src/tax_automation/rules/loader.py` dynamically synthesizes:
   - Self Contra transfer rules for all declared accounts
   - Family member transfer rules
   - Rent and landlord rules
   - Entity-specific declarative custom rules
2. Bank base rules loaded from `src/tax_automation/rules/banks/<bank>_base.py`.
3. Universal Indian merchant & banking rules loaded from `config/rules_common.json`.

### Step 3: Statement Processing & Classification
1. Detect input multi-sheet workbook at `data/<entity>/<FY>/output/consolidated_statements.xlsx` or `data/<entity>/<FY>/input/bank_statements/`.
2. Run header offset detection (`auto_header.py`) and bank fingerprint identifier (`bank_identifier.py`).
3. Classify transactions using the rule chain, assigning confidence scores (0.0 to 1.0) and human narration tags.

### Step 4: Ledger Formatting & Export
1. Write per-bank worksheets with custom column styling and auto-filters.
2. Write Tally-ready output worksheet (`For Tally`).
3. Write consolidated ledger (`Conso`) and Bank Summary.
4. Generate Monthly Pivot analysis and append colour legend.
5. Save final master workbook to `data/<entity>/<FY>/output/narrated_ledger.xlsx`:
   ```bash
   # Via FastAPI REST endpoint:
   curl -X POST "http://localhost:8000/pipeline/<entity>/<FY>/process"

   # Or via Python directly:
   python -c "from tax_automation.pipeline.narration import process_entity_narration; process_entity_narration('<entity>', '<FY>')"
   ```
