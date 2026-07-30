# Meta-Prompt: Tax Codebase Restructuring & Modularization

Act as a **Principal Software Architect & Python Data Engineer** specializing in refactoring legacy financial automation pipelines and building clean modular architectures.

Your objective is to inspect the current `Tax` repository and execute a comprehensive restructuring to transform duplicated scripts scattered across entity folders (`Aayush/`, `Ajay/`, `Sunita/`) into a centralized, production-grade Python package with Antigravity skills and workflows.

---

## Codebase Findings & Observations

### 1. Duplication — NOT Identical Copies

The `narration_engine` package exists in 3 copies (`Aayush/scripts/`, `Ajay/Scripts/`, `Sunita/Scripts/`), but **they are NOT identical**. Key divergences:

| File | Aayush | Ajay | Sunita | Notes |
|:-----|:-------|:-----|:-------|:------|
| `bank_registry.py` | 8KB (6 banks) | **14KB (12 banks)** | 8KB (6 banks) | Ajay has BOI, SBI CA/OD/Nashik/Kota/Rawatbhata/Insurance Loan/Flat Insurance/3479, HUF CA. Each entity has different `account_id` values and self-transfer UPI refs. |
| `rules_common.py` | 31KB | **46KB** | 30KB | Ajay's version has ~15KB of additional contra/transfer patterns for 10+ bank accounts |
| `rules_hdfc.py` | 10KB | 9.2KB | **11.4KB** | Each embeds different family member names & self-transfer account IDs |
| `rules_kotak.py` | 9.1KB | 7.0KB | 8.1KB | Entity-specific UPI refs and self-transfer patterns |
| `rules_sbi.py` | 3.0KB | 2.0KB | **4.0KB** | Sunita has heaviest SBI rules; Aayush has rent VPA rules |
| `exporter.py` | **59KB** | 55KB | 55KB | Aayush version has extra `assign_pivot_categories` |
| `bank_identifier.py` | 3.1KB | **3.2KB** | 3.1KB | Ajay version slightly different |
| `rules_boi.py` | ❌ | 544B | ❌ | Ajay-only bank |
| `rules_huf.py` | ❌ | 254B | ❌ | Ajay-only (placeholder) |

Truly identical files (safe to merge directly): `auto_header.py`, `classifier.py`, `cc_category_map.py`, `merchants.py`, `parse_cc.py`, `__init__.py`, `rules_axis.py`, `rules_federal.py`.

### 2. Entity-Specific Top-Level Scripts

| Script | Aayush | Ajay | Sunita | Notes |
|:-------|:-------|:-----|:-------|:------|
| `run_narration.py` | 804 lines | **955 lines** | 802 lines | Hardcoded `_BASE` paths differ; Ajay version is 150 lines larger |
| `extract_cc_statements_to_excel.py` | ✅ | ✅ | ❌ | |
| `check_contras.py` | ✅ | ❌ | ❌ | Aayush-only: contra/self-transfer verifier with BANK_MAP |
| `check_pivot.py` | ✅ | ✅ | ❌ | |
| `parse_narration_stats.py` | ✅ | ❌ | ❌ | Aayush-only analytics |
| `parse_all_stats.py` | ✅ | ❌ | ❌ | Aayush-only analytics |
| `check_narration_results.py` | ❌ | ✅ | ❌ | Ajay-only confidence checker |
| `consolidate_statements.py` | ❌ | ✅ (10KB) | ❌ | Generic fingerprint-based consolidator (PDF/CSV/encrypted XLS via `pdfplumber`, `msoffcrypto`) |
| `consolidate_ajay_statements.py` | ❌ | ✅ (7.3KB) | ❌ | Hardcoded file→sheet mappings with passwords |
| `consolidate_sunita_statements.py` | ❌ | ❌ | ✅ (4.6KB) | Hardcoded file→sheet mappings with passwords |
| `read_cc.py` | ✅ | ✅ | ❌ | |
| `run_and_verify.ps1` | ❌ | ✅ | ❌ | PowerShell pipeline: consolidate → narrate → verify |
| `run_and_verify.sh` | ❌ | ✅ | ❌ | Bash equivalent |
| `README.md` | ✅ (16KB) | ✅ (16KB) | ❌ | |
| `CC_EXTRACTION_CACHING_README.md` | ✅ | ✅ | ❌ | |

### 3. Entity-Specific Data in `bank_registry.py`

Each entity's `bank_registry.py` contains:
- **Entity-specific `account_id`**: e.g., Aayush = `HDFC 5413`, Ajay = `HDFC 5930`, Sunita = `HDFC 0094`
- **Entity-specific `sheet_name`** (Ajay only): explicit sheet names per bank
- **Self-transfer UPI refs**: Aayush has `SELF_UPI_REFS_JUPITER` + `SELF_UPI_REFS_SBI`; Ajay has empty `SELF_UPI_REFS`
- **Rent VPAs**: Aayush has `RENT_VBAS_SBI = ["4897690162095"]`
- **`OUTPUT_SHEET_NAMES`**: Ajay adds `Salary`, `Leave Encashment`, `Contra Summary`, `EquityRelated`
- **Plaintext passwords**: Ajay has `KNOWN_PASSWORDS = ["AJAY 11111967", "AJAYK11111967"]` in consolidation scripts

### 4. Data Folder Layout Differences

```
Aayush/                                    Ajay & Sunita/
├── Bank Statements/FY24,FY25,FY26/        ├── Data/FY24,FY25,FY26/Bank_Statements/
├── credit_card_statements/                └── Generated Data/
├── Capital Gains/FY25,FY26/
├── Advanced Tax/FY25,FY26/
├── Aayush Gupta Final Files - FY24/
└── Generated Data/
```

---

## Step 1: Target Modular Architecture

```text
Tax/
├── pyproject.toml
├── requirements.txt
├── src/
│   └── tax_automation/
│       ├── __init__.py
│       ├── cli.py                          # Unified CLI: `tax process --entity aayush --fy FY26`
│       │
│       ├── core/                           # Shared engine (verified identical files only)
│       │   ├── auto_header.py              # ✅ Identical across all 3
│       │   ├── bank_identifier.py          # ✅ Merge Ajay's minor diff as superset
│       │   ├── classifier.py               # ✅ Identical across all 3
│       │   ├── merchants.py                # ✅ Identical across all 3
│       │   ├── parse_cc.py                 # ✅ Identical across all 3
│       │   └── cc_category_map.py          # ✅ Identical across all 3
│       │
│       ├── exporters/
│       │   └── exporter.py                 # Merged from Aayush (superset with assign_pivot_categories)
│       │
│       ├── rules/                          # Classification rules
│       │   ├── __init__.py
│       │   ├── common_base.py              # Shared common rules (intersection of all 3 versions)
│       │   ├── loader.py                   # Rule chain builder: profile extensions → bank → common_base
│       │   ├── banks/
│       │   │   ├── hdfc_base.py            # Shared HDFC patterns (intersection)
│       │   │   ├── sbi_base.py             # Shared SBI patterns (intersection)
│       │   │   ├── kotak_base.py           # Shared Kotak patterns (intersection)
│       │   │   ├── axis.py                 # ✅ Identical across all
│       │   │   ├── federal.py              # ✅ Identical across all
│       │   │   ├── sbm.py                  # Minor diffs — use superset
│       │   │   ├── boi.py                  # Ajay-only bank
│       │   │   └── huf.py                  # Ajay-only bank type (placeholder)
│       │   └── entity_extensions/          # ⚠️ Per-entity RULE EXTENSIONS that APPEND to base rules
│       │       ├── aayush_rules.py         # Aayush-specific hdfc/kotak/sbi/common rule additions
│       │       ├── ajay_rules.py           # Ajay-specific common (~15KB extra), hdfc, kotak, sbi additions
│       │       └── sunita_rules.py         # Sunita-specific hdfc/sbi/kotak rule additions
│       │
│       ├── profiles/                       # Per-entity configuration (NOT rules — registry & metadata)
│       │   ├── __init__.py
│       │   ├── base.py                     # Profile schema, defaults, loader
│       │   ├── aayush.py                   # BANK_REGISTRY (6 banks), SELF_UPI_REFS_JUPITER/SBI,
│       │   │                               #   RENT_VBAS_SBI, OUTPUT_SHEET_NAMES, _BASE paths
│       │   ├── ajay.py                     # BANK_REGISTRY (12 banks inc. BOI/HUF/multiple SBI),
│       │   │                               #   KNOWN_PASSWORDS, OUTPUT_SHEET_NAMES (extended),
│       │   │                               #   _BASE_IN/_BASE_OUT paths
│       │   ├── sunita.py                   # BANK_REGISTRY (6 banks, different account_ids),
│       │   │                               #   KNOWN_PASSWORDS, _BASE paths
│       │   └── archit.py                   # Future placeholder
│       │
│       ├── consolidators/                  # Statement consolidation tools
│       │   ├── generic_consolidator.py     # From Ajay's consolidate_statements.py (fingerprint-based)
│       │   │                               #   Supports: PDF (pdfplumber), CSV, encrypted XLS (msoffcrypto)
│       │   └── file_mappings/              # Per-entity hardcoded file→sheet mappings (per FY)
│       │       ├── ajay_fy26.py            # Ajay's 8 files with sheet names & passwords
│       │       └── sunita_fy26.py          # Sunita's 3 files with sheet names & passwords
│       │
│       └── tools/                          # Diagnostic & analytics utilities
│           ├── check_contras.py            # From Aayush (generalized with profile BANK_MAP)
│           ├── check_narration_results.py  # From Ajay (generalized)
│           ├── parse_narration_stats.py    # From Aayush
│           ├── parse_all_stats.py          # From Aayush (Bank Summary parser)
│           └── check_pivot.py              # From Aayush/Ajay
│
├── scripts/                               # CI/CD pipeline runners
│   ├── run_and_verify.ps1                  # From Ajay (parameterized with --entity)
│   └── run_and_verify.sh                   # From Ajay (parameterized with --entity)
│
├── docs/
│   ├── README.md                           # Merged from Aayush/Ajay READMEs
│   └── CC_EXTRACTION_CACHING_README.md
│
├── data/                                   # Financial data (Git-ignored)
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

## Step 2: Rule Engine & Priority Order Architecture

When processing statements for any entity profile (e.g. `Aayush`), the classification engine loads rules via `rules/loader.py` in the following **priority cascade**:

1. **Entity Rule Extensions (`rules.entity_extensions.<entity>_rules`)**:
   - Highest Priority. Contains entity-specific additions: self-transfer patterns with hardcoded UPI refs & account numbers, family member regex patterns (e.g., `SUNITA|AJAY|ARCHIT|MEGHA|HUF|ISHWAR|PARADISE|MAINT`), rent VPA matches, contra patterns.
   - These rules are **appended before** bank base rules, so they match first.
2. **Bank-Specific Base Rules (`rules.banks.<bank>_base`)**:
   - Medium Priority. Contains bank-format-specific patterns shared across all entities (e.g., HDFC TPT format, SBI MFSS settlement codes, Kotak UPI format patterns).
3. **Common Base Rules (`rules.common_base`)**:
   - General Priority. Standard merchant dictionary matching, interest credits, GST/Tax debits, generic UPI/NEFT/RTGS patterns.
4. **Fallback Classifier**:
   - Default fallback when no explicit rule matches.

### How Entity Rule Extensions Work

Each entity extension file exports a dict keyed by bank → list of additional rules to prepend:
```python
# rules/entity_extensions/aayush_rules.py
EXTRA_COMMON_RULES = [ ... ]           # 0-2KB of Aayush-specific common rules
EXTRA_HDFC_RULES = [ ... ]             # Aayush-specific HDFC patterns (family member regex)
EXTRA_KOTAK_RULES = [ ... ]            # Aayush self-transfer UPI ref patterns
EXTRA_SBI_RULES = [ ... ]              # Aayush rent VPA rules
```

```python
# rules/entity_extensions/ajay_rules.py
EXTRA_COMMON_RULES = [ ... ]           # ~15KB of Ajay-specific contra patterns for 10+ accounts
EXTRA_HDFC_RULES = [ ... ]             # Ajay-specific HDFC patterns
EXTRA_SBI_RULES = [ ... ]              # Ajay-specific SBI patterns (fewer than Aayush/Sunita)
```

The `loader.py` concatenates: `entity_extension[bank] + bank_base + common_base` at runtime.

---

## Step 3: Profile Configuration Architecture

Each profile module (`profiles/<entity>.py`) contains:

```python
# profiles/aayush.py
PROFILE_NAME = "Aayush"
FAMILY_MEMBERS = ["SUNITA", "AJAY", "ARCHIT", "MEGHA", "HUF", "ISHWAR", "PARADISE", "MAINT"]

SELF_UPI_REFS_JUPITER = ["409319949339", "409518581802", ...]
SELF_UPI_REFS_SBI = ["409308961216", "412101194543", ...]
RENT_VBAS_SBI = ["4897690162095"]

BANK_REGISTRY = {
    "hdfc": {"display_name": "HDFC Bank", "account_id": "HDFC 5413", ...},
    "kotak": {"display_name": "Kotak Mahindra Bank", "account_id": "KOTAK 0333", ...},
    "axis": {...}, "sbi": {...}, "federal": {...}, "sbm": {...},
}

OUTPUT_SHEET_NAMES = {"For Tally", "Conso", "Bank Summary"}

KNOWN_PASSWORDS = []  # Aayush has no encrypted files

BASE_INPUT = Path(r"E:\Tax\Aayush\Generated Data")
BASE_OUTPUT = Path(r"E:\Tax\Aayush\Generated Data")

RULES_EXTENSION_MODULE = "tax_automation.rules.entity_extensions.aayush_rules"
```

---

## Step 4: Auto-Generate Workspace Skills

Create the following custom skills inside `.agents/skills/`:

1. `.agents/skills/tax-statement-processor/SKILL.md`
   - **Frontmatter**: `name: tax-statement-processor`, `description: Processes bank and credit card statements for a given entity profile, running bank identification, profile rule lookup, transaction classification, narration formatting, and Excel export with styled output sheets.`
   - **Logic**: Loads profile → loads rule chain via loader → executes classifier → exports via exporter.

2. `.agents/skills/tax-report-consolidator/SKILL.md`
   - **Frontmatter**: `name: tax-report-consolidator`, `description: Consolidates individual bank statement files (XLS, XLSX, CSV, PDF) into a single multi-sheet workbook per entity, handling password-protected files and fingerprint-based bank identification.`
   - **Logic**: Loads profile → reads file_mappings or runs generic consolidator → outputs unified workbook.

3. `.agents/skills/tax-diagnostics/SKILL.md`
   - **Frontmatter**: `name: tax-diagnostics`, `description: Runs diagnostic tools on narrated bank ledgers — contra verification, confidence score analysis, narration match rates, and pivot summaries.`
   - **Logic**: Runs check_contras, check_narration_results, parse_narration_stats, parse_all_stats for a given entity.

---

## Step 5: Auto-Generate Workspace Workflows

Create the following custom workflows inside `.antigravity/workflows/`:

1. `.antigravity/workflows/restructure-codebase.md`
   - **Phase 1**: Create `src/tax_automation/` package structure with `__init__.py` files.
   - **Phase 2**: Move identical engine files to `core/`. Merge `exporter.py` from Aayush (superset).
   - **Phase 3**: Diff each entity's `rules_common.py`, `rules_hdfc.py`, `rules_kotak.py`, `rules_sbi.py` against each other. Extract shared intersection into `_base.py` files. Extract entity-specific deltas into `entity_extensions/<entity>_rules.py`.
   - **Phase 4**: Extract each entity's `bank_registry.py` into `profiles/<entity>.py` with `BANK_REGISTRY`, `SELF_UPI_REFS`, `RENT_VBAS`, `OUTPUT_SHEET_NAMES`, `KNOWN_PASSWORDS`, `_BASE` paths.
   - **Phase 5**: Move diagnostic/analytics scripts to `tools/`. Generalize hardcoded paths to use profile loader.
   - **Phase 6**: Move consolidation scripts to `consolidators/`. Generalize `run_narration.py` into `cli.py` with `--entity` parameter.
   - **Phase 7**: Move pipeline runners (`run_and_verify.ps1/.sh`) to `scripts/`, parameterize with `--entity`.
   - **Phase 8**: Move READMEs to `docs/`.
   - **Phase 9**: Validate by running narration for all 3 entities and comparing output against original.
   - **Human Approval Gate**: Before deleting original entity script folders.

2. `.antigravity/workflows/process-entity-taxes.md`
   - **Step 1**: Prompt for target entity and Fiscal Year.
   - **Step 2**: Run consolidation (if individual bank files exist).
   - **Step 3**: Run narration engine with entity profile.
   - **Step 4**: Run diagnostics (contra check, confidence analysis).
   - **Step 5**: Present summary for human review.

3. `.antigravity/workflows/add-new-entity.md`
   - **Step 1**: Create profile module in `profiles/<entity>.py`.
   - **Step 2**: Create entity rule extensions if needed.
   - **Step 3**: Create data directory structure.
   - **Step 4**: Test with sample statement.

---

## Step 6: Save & Persist to Repository Memory

Save this Meta-Prompt file into project memory directory:
- `.memory/prompts/restructure-tax-codebase.md`

---

## Execution Instructions

When running this Meta-Prompt:
1. **NEVER naively merge** rule files. Diff each entity's version line-by-line to extract the shared base and entity-specific extensions.
2. **Preserve all entity-specific data**: self-transfer UPI refs, rent VPAs, family member regexes, account IDs, passwords, OUTPUT_SHEET_NAMES, _BASE paths.
3. **Keep entity data folders as-is** under `data/` — Aayush's richer folder structure (Capital Gains, Advanced Tax, etc.) must not be lost.
4. **Validate output parity**: After restructuring, run narration for all 3 entities and diff the output Excel files against originals to ensure zero regression.
5. Provide single-line slash commands for users to trigger workflows upon completion:
   - `/restructure-codebase`
   - `/process-entity-taxes`
   - `/add-new-entity`
