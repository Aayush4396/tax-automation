# Tax Automation System

**Automated Financial Statement Consolidation, Transaction Classification, and Tax Ledger Accounting Engine.**

---

## Product Overview

The **Tax Automation System** is an end-to-end accounting and tax-preparation platform designed for taxpayers, family offices, and accounting professionals. It automates the ingestion of raw, multi-format bank statements (PDF, Excel, CSV), resolves cryptic banking and UPI transactions into human-readable accounting heads, balances inter-account transfers, and generates audit-ready Excel ledgers formatted for immediate tax filing and Tally ingestion.

Designed around a **zero-code, plug-and-play architecture**, any individual or family entity can be onboarded in seconds through declarative profiles without modifying Python source code.

---

## Business Problem & Value Proposition

### The Challenge
Personal and business tax filings in India are encumbered by fragmented financial data:
- **Cryptic Narrations**: Banking portals record transactions with opaque references (e.g., `UPI/CR/0000000000/MERCHANT/BANK/1234567`, `NEFT-N12345-TRANSFER`).
- **Contra & Self-Transfer Distortion**: Transfers between personal bank accounts often get miscalculated as taxable income or deductible expenses.
- **Related-Party Complexity**: Routine funds transferred among family members, dependents, or entities (e.g., HUF accounts) require dedicated bookkeeping.
- **Format Inconsistency**: Each financial institution (HDFC, SBI, Axis, Kotak, Federal, etc.) uses proprietary column structures, date formats, and password encryption schemes.

### The Solution
Tax Automation standardizes and automates this workflow:
- **Automated Ingestion**: Directly ingests XLS, XLSX, CSV, and encrypted PDF statements.
- **Context-Aware Classification**: Accurately labels merchants, utility providers, salary credits, investments, and routine living expenses using a dual rule compiler.
- **Contra Symmetry Engine**: Pairs debit and credit legs of self-transfers across accounts to prevent double-counting.
- **Standardized Reporting**: Exports a comprehensive, color-coded master ledger featuring Tally-compatible outputs, multi-account timelines, and monthly category pivots.

---

## Key Capabilities

- **Zero-Code Taxpayer Onboarding**: Command-line generator scaffolds new entity profiles and directory structures automatically.
- **Preconfigured Banking Schemas**: Out-of-the-box column definitions and signal recognizers for major Indian banks (HDFC, SBI, Kotak, Axis, Bank of India, Federal Bank, SBM Bank, HUF, ICICI, and generic fallbacks).
- **Dynamic Rule Compilation**: Synthesizes custom contra rules, family transfers, rent payments, and taxpayer-specific rules at runtime.
- **Universal Merchant Dictionary**: Built-in normalization for 60+ common Indian digital commerce, payment gateway, and investment transaction patterns.
- **In-Memory Credential Handling**: Encrypted bank statements are decrypted in-memory using environment variables without writing unencrypted data or passwords to disk.
- **Privacy by Design**: All processing runs locally on your machine. Financial data is strictly ignored by version control to guarantee zero data leakage.

---

## Operational Guide: How to Use

No Python coding is required to operate the system for any entity.

### 1. Initial Setup

Ensure [Python 3.10+](https://www.python.org/downloads/) is installed.

```bash
# Clone the repository
git clone https://github.com/Aayush4396/tax-automation.git
cd tax-automation

# Set up virtual environment
python -m venv .venv

# Activate environment:
# Windows PowerShell:
.venv\Scripts\Activate.ps1
# Linux / macOS:
source .venv/bin/activate

# Install dependencies and package
pip install -r requirements.txt
pip install -e .
```

---

### 2. Entity Onboarding

Initialize a new taxpayer entity using the CLI onboarding utility:

```bash
python -m tax_automation init-entity --entity demo_entity --name "Sample Taxpayer" --pan XXXXX0000X --fy FY26
```

This scaffolds:
- `config/entities/demo_entity.json` (declarative configuration)
- `data/demo_entity/FY26/input/bank_statements/` (raw statement input directory)
- `data/demo_entity/FY26/output/` (generated report directory)

---

### 3. Bank Account Configuration

Open `config/entities/demo_entity.json` to declare the taxpayer's bank accounts. Assign standard bank types (`hdfc`, `sbi`, `kotak`, `axis`, `boi`, `federal`, `sbm`, `icici`, `generic`):

```json
"accounts": [
  {
    "account_key": "hdfc",
    "bank": "hdfc",
    "account_id": "HDFC 1001",
    "sheet_name": "HDFC 1001",
    "display_name": "HDFC Bank Savings",
    "meta_signals_extra": ["1001"]
  },
  {
    "account_key": "sbi",
    "bank": "sbi",
    "account_id": "SBI 2002",
    "sheet_name": "SBI 2002",
    "display_name": "State Bank of India",
    "meta_signals_extra": ["2002"]
  }
]
```

*(Optional: Declare family members, rent keywords, or landlord VPAs in the same file to enable automatic relationship tagging.)*

---

### 4. Statement Processing

1. Place downloaded bank statement files into the entity's input folder:
   ```text
   data/demo_entity/FY26/input/bank_statements/
   ```

2. Execute the processing pipeline:
   ```bash
   python -m tax_automation process --entity demo_entity --fy FY26
   ```

*(Optional: If consolidating separate raw statements into a single multi-sheet workbook first, run `python -m tax_automation consolidate --entity demo_entity --fy FY26`)*

---

### 5. Reviewing Financial Deliverables

The master ledger is generated at:
```text
data/demo_entity/FY26/output/narrated_ledger.xlsx
```

To run automated contra-balance diagnostics:
```bash
python -m tax_automation.tools.check_contras --entity demo_entity --fy FY26
```

---

## Delivered Workbooks & Financial Reports

The generated Excel workbook contains structured worksheets tailored for audit and filing:

| Worksheet | Purpose & Description |
| :--- | :--- |
| **For Tally** | Standardized, single-entry accounting sheet ready for Tally XML import or direct CA ledger entry. |
| **Conso** | Master chronological audit trail merging all transactions across all accounts with running balances. |
| **Bank Summary** | Institutional summary listing Opening Balance, Total Debits, Total Credits, and Closing Balance per bank. |
| **Monthly Pivot** | Matrix breakdown of monthly expenditures aggregated by accounting head and category. |
| **Bank Tabs** | Dedicated worksheets for each individual account (`HDFC 1001`, `SBI 2002`, etc.) with classification tags. |
| **Colour Legend** | Visual reference key explaining confidence scoring tiers and flag statuses. |

---

## Convenience Runners

Pre-configured shell runners provide single-step execution:

- **Windows PowerShell**:
  ```powershell
  .\scripts\run_and_verify.ps1 -Entity demo_entity -FY FY26
  ```
- **Linux / macOS**:
  ```bash
  ./scripts/run_and_verify.sh demo_entity FY26
  ```

---

## Credential & Encryption Management

For statements secured by bank passwords (e.g., statement PDFs/Excels):
1. Add passwords to your local `.env` file:
   ```bash
   ENTITY_SBI_PASSWORD="YOUR_PASSWORD_HERE"
   ```
2. Reference the variable name in `config/consolidation/<entity>_<fy>.json`:
   ```json
   {
     "filename": "Bank_Statement.xlsx",
     "sheet_name": "SBI",
     "password_env_var": "ENTITY_SBI_PASSWORD"
   }
   ```
Statements are decrypted in-memory during extraction. Credentials and decrypted files are never persisted to disk or external services.

---

## Security, Privacy & Compliance Governance

- **100% Local Execution**: All computations occur locally. No financial records, PII, or balances leave your machine.
- **Repository Isolation**: Pre-configured `.gitignore` rules prevent `.xlsx`, `.xls`, `.pdf`, `.csv`, and `.log` files from being staged or committed.
- **Stateless Operation**: Does not require external database connections or cloud credentials.

---

## Technical Specifications & Architecture

```text
tax-automation/
├── src/tax_automation/
│   ├── cli.py                  # CLI entry point (init-entity, consolidate, process)
│   ├── config_loader.py        # Schema validation, path resolution, bank registry
│   ├── core/                   # Header detection, bank fingerprinting, merchant signals
│   ├── consolidators/          # In-memory decryptor & multi-sheet consolidator
│   ├── rules/                  # Dynamic rule compiler & bank-specific rules
│   ├── pipeline/               # Narration classification & statement pipelines
│   ├── exporters/              # Master Excel ledger, Tally formatting, pivot tables
│   └── tools/                  # Diagnostics: check_contras, narration_stats
├── config/
│   ├── entities/               # Taxpayer profiles (declarative JSON configs)
│   ├── banks/                  # Reusable bank schemas (hdfc, sbi, kotak, etc.)
│   ├── consolidation/          # Multi-statement file-to-sheet maps
│   └── rules_common.json       # Universal Indian merchant/banking rules
├── data/                       # Local data hierarchy (gitignored financial data)
│   ├── <entity_id>/<FY>/
│   │   ├── input/bank_statements/
│   │   └── output/
│   └── README.md
└── scripts/
    ├── run_and_verify.ps1      # 1-click PowerShell runner
    └── run_and_verify.sh       # 1-click Bash runner
```

### Verification & Testing Suite

```bash
# Execute unit test suite
python -m unittest discover -s src/tax_automation/tests

# Verify formatting compliance (Black)
black --check src

# Verify code quality & standards (Flake8)
flake8 src --max-line-length=88
```

---

## License

MIT License. Free to use for personal, family office, and commercial accounting workflows.