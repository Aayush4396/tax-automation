---
name: tax-statement-processor
description: Config-driven processor for bank and credit card statements. Loads JSON profile configuration, builds dynamic rule chains, classifies transactions, and generates formatted Excel ledgers.
---

# Tax Statement Processor Skill

## Objective
Process bank statements and credit card statements for a designated entity profile (`aayush`, `ajay`, `sunita`, etc.) and Financial Year (`FY24`, `FY25`, `FY26`).

---

## Execution Steps

### Step 1: Configuration & Profile Loading
1. Read profile JSON configuration from `config/entities/<entity>.json`.
2. Retrieve bank registry mappings, account IDs, family member regex lists, self-transfer UPI references, and landlord VPAs.
3. Check for statement decryption keys in `.env` if files are password protected.

### Step 2: Dynamic Rule Chain Construction
1. Load common base classification rules from `src/tax_automation/rules/common_base.py`.
2. Load bank base rules from `src/tax_automation/rules/banks/<bank>_base.py`.
3. Load entity-specific rule extensions from `src/tax_automation/rules/entity_extensions/<entity>_rules.py`.
4. Construct rule evaluation order: `entity_extensions` (highest) → `bank_base` → `common_base` → `fallback`.

### Step 3: Statement Processing & Classification
1. Detect input multi-sheet workbook at `data/<entity>/Generated Data/<FY>/All Bank Statements*.xlsx`.
2. Run header offset detection (`auto_header.py`) and bank fingerprint identifier (`bank_identifier.py`).
3. Classify transactions using the rule chain, assigning confidence scores (0.0 to 1.0) and human narration tags.
4. Process credit card statements if present in `data/<entity>/credit_card_statements/`.

### Step 4: Ledger Formatting & Export
1. Write per-bank worksheets with custom column styling and auto-filters.
2. Write Tally-ready output worksheet (`For Tally`).
3. Write consolidated ledger (`Conso`) and Bank Summary.
4. Generate Monthly Pivot analysis and append legend.
5. Save final workbook to `data/<entity>/Generated Data/<FY>/<Entity>_Consolidated_Bank_Ledger_<FY>.xlsx`.
