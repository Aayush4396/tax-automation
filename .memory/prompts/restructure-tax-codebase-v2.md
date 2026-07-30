# Meta-Prompt: Tax Codebase Restructuring & Modularization (v2)

Act as a **Principal Software Architect & Python Data Engineer** specializing in refactoring legacy financial automation pipelines, externalizing configuration, and building clean modular architectures.

Your objective is to inspect the current `Tax` repository and execute a comprehensive restructuring to transform duplicated scripts scattered across entity folders (`Aayush/`, `Ajay/`, `Sunita/`) into a centralized, production-grade Python package with externalized JSON/YAML configs, profile modules, and Antigravity skills/workflows.

---

## Codebase Findings & File Inventory

### 1. Duplication — Divergent Files Across Entities

The `narration_engine` package exists in 3 copies (`Aayush/scripts/`, `Ajay/Scripts/`, `Sunita/Scripts/`), but **they are NOT identical**. Key divergences:

| File | Aayush | Ajay | Sunita | Status / Merge Strategy |
|:-----|:-------|:-----|:-------|:------------------------|
| `bank_registry.py` | 8KB (6 banks) | **14KB (12 banks)** | 8KB (6 banks) | ⚠️ **Extract to `config/entities/<entity>.json`** |
| `rules_common.py` | 31KB | **46KB** | 30KB | ⚠️ **Extract base rules to `rules/common_base.py`, deltas to `rules/entity_extensions/`** |
| `rules_hdfc.py` | 10KB | 9.2KB | **11.4KB** | ⚠️ **Extract family member regex to entity config; base rules to `rules/banks/hdfc_base.py`** |
| `rules_kotak.py` | 9.1KB | 7.0KB | 8.1KB | ⚠️ **Extract UPI refs to entity config; base rules to `rules/banks/kotak_base.py`** |
| `rules_sbi.py` | 3.0KB | 2.0KB | **4.0KB** | ⚠️ **Extract rent VPAs to entity config; base rules to `rules/banks/sbi_base.py`** |
| `exporter.py` | **59KB** | 55KB | 55KB | ✅ Merge Aayush version (superset with `assign_pivot_categories`) |
| `bank_identifier.py` | 3.1KB | **3.2KB** | 3.1KB | ✅ Merge Ajay version (superset) |
| `rules_boi.py` | ❌ | 544B | ❌ | ✅ Move to `rules/banks/boi.py` |
| `rules_huf.py` | ❌ | 254B | ❌ | ✅ Move to `rules/banks/huf.py` |

**Identical Files (Safe Direct Merge)**: `auto_header.py`, `classifier.py`, `cc_category_map.py`, `merchants.py`, `parse_cc.py`, `__init__.py`, `rules_axis.py`, `rules_federal.py`.

---

## Hardcoded Logic Inventory & Externalization Plan

A systematic scan of all Python files revealed **9 distinct categories of hardcoded logic** that must be externalized into JSON/YAML configuration files, `.env` files, or parameterized CLI options:

### 1. Hardcoded Values Inventory

| Category | Hardcoded Value / Pattern | Found In File(s) | Target Externalization Format |
|:---------|:--------------------------|:-----------------|:------------------------------|
| **Filesystem Paths** | `Path(r"E:\Tax\Aayush\Generated Data")`, `_BASE_IN`, `_BASE_OUT` | `run_narration.py`, `consolidate_*.py`, `check_contras.py` | **CLI `--data-dir` arg + dynamic path resolution from entity & FY** |
| **Passwords & Secrets** | `KNOWN_PASSWORDS = ["AJAY 11111967", "AJAYK11111967"]` | `consolidate_statements.py`, `consolidate_ajay_statements.py`, `consolidate_sunita_statements.py` | **Environment Variables / `.env` file (`AJAY_PDF_PASSWORDS=...`)** |
| **Account IDs & Names** | `"HDFC 5413"`, `"HDFC 5930"`, `"HDFC 0094"`, `"KOTAK 0333"`, `"BOI 6699"`, `"SBI 1227"` | `bank_registry.py` (across all 3 folders) | **JSON Entity Config (`config/entities/<entity>.json`)** |
| **Self-Transfer UPI Refs** | `SELF_UPI_REFS_JUPITER = ["409319949339", ...]`, `SELF_UPI_REFS_SBI = [...]` | `bank_registry.py` (Aayush/Sunita) | **JSON Entity Config (`config/entities/<entity>.json`)** |
| **Landlord Rent VPAs** | `RENT_VBAS_SBI = ["4897690162095"]` | `bank_registry.py` (Aayush/Sunita) | **JSON Entity Config (`config/entities/<entity>.json`)** |
| **Family Member Regex** | `r"SUNITA\|AJAY\|AAYUSH\|ARCHIT\|MEGHA\|HUF\|ISHWAR\|PARADISE\|MAINT"` | `rules_hdfc.py` (across all 3 folders) | **JSON Entity Config (`family_members` list in `config/entities/<entity>.json`)** |
| **Sheet Skip Lists** | `OUTPUT_SHEET_NAMES = {"For Tally", "Conso", "Bank Summary"}` vs Ajay's extended list | `bank_registry.py`, `parse_narration_stats.py`, `check_narration_results.py` | **JSON Entity Config (`output_sheet_names` array)** |
| **File-to-Sheet Mappings** | `files_mapping = [("Ajay Acct_Statement_...xls", "HDFC 5930", None), ...]` | `consolidate_ajay_statements.py`, `consolidate_sunita_statements.py` | **JSON Consolidation Map (`config/consolidation/<entity>_<fy>.json`)** |
| **Merchant VPA Map** | `MERCHANT_MAP = [("zomato", ...), ("swiggy", ...), ("amazon", ...)]` | `merchants.py` | **JSON Merchant Map (`config/merchants.json`)** |
| **CC Categories & Themes** | `CC_NARRATION_MAP`, `_CC_CATEGORIES`, Airtel Wifi amount overrides | `cc_category_map.py`, `parse_cc.py` | **JSON CC Categories Config (`config/cc_categories.json`)** |
| **Header Row Keywords** | `_DATE_KEYS`, `_AMT_KEYS` sets | `auto_header.py` | **JSON Header Keywords (`config/header_keywords.json`)** |
| **Exporter Theme & Style** | `COLOUR_MAP`, sheet rename maps, hidden column lists | `exporter.py` | **JSON Exporter Theme (`config/exporter_theme.json`)** |
| **Cross-Bank Base Rules** | Standard regex rules (`IRCTC`, `CEMTEX`, `Sanofi`, `BESCOM`, `NSDL`, etc.) | `common_base.py` | **JSON Declarative Rules (`config/rules_common.json`)** |

---

### 2. Externalization Formats & Schema Examples

#### A. Entity JSON Configuration (`config/entities/aayush.json`)
```json
{
  "entity_id": "aayush",
  "display_name": "Aayush Gupta",
  "family_members": ["SUNITA", "AJAY", "ARCHIT", "MEGHA", "HUF", "ISHWAR", "PARADISE", "MAINT"],
  "rent_vpas": ["4897690162095"],
  "self_upi_refs": {
    "jupiter": ["409319949339", "409518581802", "409860235500", "410013514219", "410480092425", "410798005765", "413856144623", "413856342655", "413859249444"],
    "sbi": ["409308961216", "412101194543", "416418674665", "416418731041"]
  },
  "output_sheet_names": ["For Tally", "Conso", "Bank Summary"],
  "banks": {
    "hdfc": {
      "display_name": "HDFC Bank",
      "account_id": "HDFC 5413",
      "meta_signals": ["HDFC BANK", "Withdrawal Amt", "Closing Balance", "Statement of accounts", "Account No :"],
      "header_signals": ["Withdrawal Amt.", "Deposit Amt.", "Closing Balance", "Chq./Ref.No."],
      "col_date": "Date",
      "col_particulars": "Narration",
      "col_dr": "Withdrawal Amt.",
      "col_cr": "Deposit Amt.",
      "col_balance": "Closing Balance",
      "col_ref": "Chq./Ref.No.",
      "col_value_date": "Value Dt",
      "rules_module": "tax_automation.rules.banks.hdfc_base"
    },
    "kotak": {
      "display_name": "Kotak Mahindra Bank",
      "account_id": "KOTAK 0333",
      "col_date": "Transaction Date",
      "col_particulars": "Description",
      "col_dr": "DR",
      "col_cr": "CR",
      "col_balance": "Balance",
      "col_ref": "Chq / Ref No.",
      "col_value_date": "Value Date"
    }
  }
}
```

#### B. Consolidation Map (`config/consolidation/ajay_fy26.json`)
```json
{
  "entity": "ajay",
  "fy": "FY26",
  "output_filename": "All Bank Statements Ajay FY26.xlsx",
  "files": [
    { "filename": "Ajay Acct_Statement_XXXXXXXX5930_14042026.xls", "sheet_name": "HDFC 5930", "password_env_var": null },
    { "filename": "Ajay Current account account SBI.xlsx", "sheet_name": "SBI CA", "password_env_var": "AJAY_SBI_PASSWORD" },
    { "filename": "SBI Insurance loan account Nashik.pdf", "sheet_name": "SBI Insurance Loan", "password_env_var": "AJAY_INSURANCE_LOAN_PASSWORD" }
  ]
}
```

#### C. Environment Variables File (`.env.example`)
```env
# Sensitive Statement Passwords
AJAY_SBI_PASSWORD=AJAY 11111967
AJAY_INSURANCE_LOAN_PASSWORD=AJAYK11111967
SUNITA_SBI_PASSWORD=AJAY 11111967
```

---

## Step 1: Target Modular Architecture

```text
Tax/
├── pyproject.toml
├── requirements.txt
├── .env.example                            # Password & secret environment template
│
├── config/                                 # 📂 JSON Configuration Storage
│   ├── entities/                           # Per-entity configuration files
│   │   ├── aayush.json                     # Aayush accounts, UPI refs, rent VPAs, sheet skip list
│   │   ├── ajay.json                       # Ajay accounts (12 banks inc. BOI/HUF), extended sheet list
│   │   ├── sunita.json                     # Sunita account IDs & bank configurations
│   │   └── archit.json                     # Archit placeholder
│   │
│   └── consolidation/                      # Per-entity per-FY statement consolidation maps
│       ├── ajay_fy26.json                  # File-to-sheet mappings for Ajay FY26
│       ├── sunita_fy26.json                # File-to-sheet mappings for Sunita FY26
│       └── aayush_fy26.json                # File-to-sheet mappings for Aayush FY26
│
├── src/
│   └── tax_automation/
│       ├── __init__.py
│       ├── cli.py                          # Unified CLI: `tax process --entity aayush --fy FY26`
│       │
│       ├── config_loader.py                # Loads & validates JSON configs and .env passwords
│       │
│       ├── core/                           # Shared processing engine
│       │   ├── auto_header.py              # Header row offset detector
│       │   ├── bank_identifier.py          # Bank fingerprint matcher
│       │   ├── classifier.py               # Classification driver
│       │   ├── merchants.py                # Merchant dictionary & fuzzy match
│       │   ├── parse_cc.py                 # CC statement parser
│       │   └── cc_category_map.py          # CC category mappings
│       │
│       ├── exporters/
│       │   └── exporter.py                 # Excel ledger exporter & formatter
│       │
│       ├── rules/                          # Classification rules engine
│       │   ├── __init__.py
│       │   ├── common_base.py              # Shared common rules
│       │   ├── loader.py                   # Runtime rule chain builder (entity additions + bank + base)
│       │   ├── banks/                      # Shared bank base rules
│       │   │   ├── hdfc_base.py
│       │   │   ├── sbi_base.py
│       │   │   ├── kotak_base.py
│       │   │   ├── axis.py
│       │   │   ├── federal.py
│       │   │   ├── sbm.py
│       │   │   ├── boi.py                  # Bank of India rules
│       │   │   └── huf.py                  # HUF rules
│       │   └── entity_extensions/          # Dynamic rule extensions driven by JSON config
│       │       ├── aayush_rules.py
│       │       ├── ajay_rules.py           # Ajay extra contra patterns (~15KB)
│       │       └── sunita_rules.py
│       │
│       ├── consolidators/                  # Statement consolidators
│       │   ├── generic_consolidator.py     # Config-driven statement consolidator
│       │   └── pdf_extractor.py            # PDF table extraction helper (pdfplumber)
│       │
│       └── tools/                          # Generalized diagnostic utilities
│           ├── check_contras.py            # Config-driven contra checker
│           ├── check_narration_results.py  # Confidence & match rate analyzer
│           ├── parse_narration_stats.py    # Narration statistics generator
│           └── parse_all_stats.py          # Summary report generator
│
├── scripts/                               # Automation runners
│   ├── run_and_verify.ps1                  # PowerShell wrapper: `.\run_and_verify.ps1 -Entity Ajay -FY FY26`
│   └── run_and_verify.sh                   # Bash wrapper
│
├── docs/
│   ├── README.md                           # Comprehensive documentation
│   └── CC_EXTRACTION_CACHING_README.md
│
├── data/                                   # Financial data storage (Git-ignored)
│   ├── Aayush/
│   │   ├── Bank Statements/FY24,FY25,FY26/
│   │   ├── credit_card_statements/
│   │   ├── Capital Gains/FY25,FY26/
│   │   ├── Advanced Tax/FY25,FY26/
│   │   ├── Final Files - FY24/
│   │   └── Generated Data/
│   ├── Ajay/
│   │   ├── Data/FY24,FY25,FY26/Bank_Statements/
│   │   └── Generated Data/
│   ├── Sunita/
│   │   ├── Data/FY24,FY25,FY26/Bank_Statements/
│   │   └── Generated Data/
│   └── Archit/
│
├── .agents/skills/
└── .antigravity/workflows/
```

---

## Step 2: Hardcoded Logic Extraction & Generalization Execution Plan

### Phase 1: Configuration Extraction
1. Create `config/entities/aayush.json`, `config/entities/ajay.json`, `config/entities/sunita.json`.
2. Move all account IDs, display names, bank metadata signals, column mappings, UPI reference numbers, landlord VPAs, family member lists, and output sheet skip lists from `bank_registry.py` into their respective entity JSON files.
3. Create `config/consolidation/<entity>_<fy>.json` files for file-to-sheet mappings.
4. Create `.env.example` and move statement passwords to environment variables.

### Phase 2: Core Engine Refactoring
1. Build `src/tax_automation/config_loader.py` to load JSON configs dynamically based on `--entity` parameter.
2. Update `bank_identifier.py` to read bank registry schemas from `config_loader` instead of static `BANK_REGISTRY` dict.
3. Refactor `rules_hdfc.py` to pull family member regex strings dynamically from loaded entity config:
   ```python
   # Dynamic family member regex pattern build
   family_pattern = "|".join(re.escape(name) for name in profile_config["family_members"])
   ```
4. Refactor `rules_kotak.py` and `rules_sbi.py` to pull self-transfer UPI refs and rent VPAs from loaded entity config.

### Phase 3: Rule Deduplication & Extension Chain
1. Diff `rules_common.py` across all 3 folders:
   - Move shared intersection rules into `rules/common_base.py`.
   - Move Ajay's 15KB of extra contra patterns into `rules/entity_extensions/ajay_rules.py`.
2. Build `rules/loader.py` to construct the runtime rule chain:
   `entity_extensions[bank] + bank_base_rules + common_base_rules`

### Phase 4: CLI & Tool Generalization
1. Transform `run_narration.py` into `src/tax_automation/cli.py` with standard arguments:
   `python -m tax_automation process --entity <name> --fy <FY> [--data-dir <path>]`
2. Generalize `check_contras.py`: Replace static `BANK_MAP` dict with dynamic dictionary constructed from loaded entity JSON config.
3. Generalize output filename generation: Replace `f"Aayush_Consolidated_Bank_Ledger_{fy}.xlsx"` with `f"{entity_name}_Consolidated_Bank_Ledger_{fy}.xlsx"`.

---

## Step 3: Auto-Generate Workspace Skills

Create the following custom skills inside `.agents/skills/`:

1. `.agents/skills/tax-statement-processor/SKILL.md`
   - **Frontmatter**: `name: tax-statement-processor`, `description: Config-driven processor for bank and credit card statements. Loads JSON profile configuration, builds dynamic rule chains, classifies transactions, and generates formatted Excel ledgers.`
2. `.agents/skills/tax-report-consolidator/SKILL.md`
   - **Frontmatter**: `name: tax-report-consolidator`, `description: Consolidates multi-format bank statement files (XLS, XLSX, CSV, PDF) into single multi-sheet workbooks using JSON consolidation maps and encrypted file passwords from environment variables.`
3. `.agents/skills/tax-diagnostics/SKILL.md`
   - **Frontmatter**: `name: tax-diagnostics`, `description: Diagnostic toolsuite for verifying contras, analyzing classification confidence scores, calculating human narration match rates, and inspecting bank pivots.`

---

## Step 4: Auto-Generate Workspace Workflows

Create the following custom workflows inside `.antigravity/workflows/`:

1. `.antigravity/workflows/restructure-codebase.md`
   - **Steps**:
     1. Extract JSON configs (`config/entities/`, `config/consolidation/`) and `.env.example`.
     2. Create `src/tax_automation/` package and `config_loader.py`.
     3. Merge core engine files (`auto_header.py`, `bank_identifier.py`, `classifier.py`, `merchants.py`, `parse_cc.py`, `exporter.py`).
     4. Build rule base modules (`rules/banks/`, `rules/common_base.py`) and entity extension modules (`rules/entity_extensions/`).
     5. Generalize diagnostic scripts (`tools/`) and CLI runner (`cli.py`).
     6. Run validation tests comparing output workbooks for Aayush, Ajay, and Sunita against originals to ensure 100% output parity.
     7. **Human Approval Gate**: Review parity test report before deleting old entity script directories.

2. `.antigravity/workflows/process-entity-taxes.md`
   - **Steps**:
     1. Prompt for target entity (`aayush`, `ajay`, `sunita`, `archit`) and Fiscal Year (`FY24`, `FY25`, `FY26`).
     2. Run statement consolidator using JSON consolidation map.
     3. Run narration classification engine with JSON profile config.
     4. Run contra & confidence diagnostics.
     5. Display summary report for human review.

3. `.antigravity/workflows/add-new-entity.md`
   - **Steps**:
     1. Create `config/entities/<new_entity>.json` with account IDs and bank registry schemas.
     2. Create `config/consolidation/<new_entity>_<fy>.json` with statement file mappings.
     3. Add passwords to `.env` if files are encrypted.
     4. Test pipeline on sample statements.

---

## Step 5: Save & Persist to Repository Memory

Save this Meta-Prompt file into project memory directory:
- `.memory/prompts/restructure-tax-codebase-v2.md`

---

## Execution Instructions

When running this Meta-Prompt:
1. **Zero Hardcoded Data in Source Code**: Ensure all filesystem paths, account IDs, names, passwords, UPI refs, sheet skip lists, and file mappings are completely removed from `.py` source files and moved into `config/entities/*.json`, `config/consolidation/*.json`, or `.env`.
2. **Output Parity Verification**: Run narration pipeline for all 3 entities before and after restructuring. Verify that row counts, confidence scores, and narration strings match 100%.
3. Provide single-line slash commands for users to trigger workflows upon completion:
   - `/restructure-codebase`
   - `/process-entity-taxes`
   - `/add-new-entity`
