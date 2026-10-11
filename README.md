# Tax Automation

A modular, config-driven Python system for automating Indian tax accounting, bank statement consolidation, transaction narration classification, and master Excel ledger generation.

Designed for plug-and-play onboarding: any taxpayer can onboard their accounts with **zero Python code changes** via declarative JSON configuration and standard CLI commands.

---

## Key Features

- **Zero-Code Taxpayer Onboarding**: Scaffold a new taxpayer profile and canonical directory tree in seconds using `init-entity`.
- **Reusable Bank Schema Library**: Preconfigured column definitions, header signals, and statement formats for major Indian banks (HDFC, SBI, Kotak, Axis, BOI, Federal/Jupiter, SBM, HUF, ICICI, and generic fallbacks).
- **Dynamic Rule Compiler**: Automatically synthesizes self-contra rules, family transfer classifications, rent detections, and custom rules at runtime based on the taxpayer's profile.
- **Universal Merchant Rules**: Over 60+ universal Indian merchant and banking transaction patterns (UPI, NEFT, RTGS, IMPS, utility bills, investments, salary).
- **Multi-Format Ingestion**: Ingests statements across Excel (XLS, XLSX), CSV, and PDF formats, with automatic in-memory password decryption.
- **Master Excel Ledger Generation**: Exports fully formatted workbooks with individual bank sheets, Tally-ready import sheets (`For Tally`), consolidated chronologies (`Conso`), bank opening/closing balances (`Bank Summary`), and monthly category breakdowns (`Monthly Pivot`).
- **Privacy & Security by Design**: Personal financial statements and generated files are automatically ignored by `.gitignore`. Repository tracks directory structure via `.gitkeep` files without exposing sensitive data.

---

## Prerequisites

- **Python**: 3.10 or higher
- **Virtual Environment**: Recommended

---

## Installation

```bash
# Clone the repository
git clone https://github.com/Aayush4396/tax-automation.git
cd tax-automation

# Create and activate virtual environment
python -m venv .venv
# Windows PowerShell:
.venv\Scripts\Activate.ps1
# Linux / macOS:
source .venv/bin/activate

# Install dependencies and package in editable mode
pip install -r requirements.txt
pip install -e .
```

---

## Quick Start: Onboarding a New Taxpayer

### 1. Scaffold Profile & Directories
```bash
python -m tax_automation init-entity --entity john --name "John Doe" --pan ABCDE1234F --fy FY26
```
This automatically creates:
- `config/entities/john.json` (profile template)
- `data/john/FY26/input/bank_statements/` (statement drop folder)
- `data/john/FY26/output/` (ledger output folder)

### 2. Configure Declared Accounts
In `config/entities/john.json`, declare the bank accounts:
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

### 3. Place Statements & Run Pipeline
Drop bank statements into `data/john/FY26/input/bank_statements/` and run:

```bash
# Step 1: Consolidate individual statements into a multi-sheet workbook (optional)
python -m tax_automation consolidate --entity john --fy FY26

# Step 2: Run narration classification & export master ledger
python -m tax_automation process --entity john --fy FY26

# Step 3: Run diagnostic checks
python -m tax_automation.tools.check_contras --entity john --fy FY26
```

Final output is saved to:
`data/john/FY26/output/narrated_ledger.xlsx`

---

## Architecture Overview

```text
tax-automation/
├── src/tax_automation/
│   ├── cli.py                  # CLI entry point (init-entity, consolidate, process)
│   ├── config_loader.py        # Schema validation & path resolution
│   ├── core/                   # Bank identification, auto-header, merchants
│   ├── consolidators/          # Ingests XLS, XLSX, CSV, PDF statements
│   ├── rules/                  # Dynamic rule compiler & bank-specific rules
│   ├── pipeline/               # Narration & consolidation pipelines
│   ├── exporters/              # Master Excel ledger & Tally exporter
│   └── tools/                  # Diagnostic utilities (check_contras, narration stats)
├── config/
│   ├── entities/               # Taxpayer profiles (aayush.json, ajay.json, etc.)
│   ├── banks/                  # Reusable bank schemas (hdfc.json, sbi.json, etc.)
│   ├── consolidation/          # File-to-sheet consolidation maps
│   └── rules_common.json       # Universal Indian merchant & banking rules
├── data/
│   ├── <entity_id>/
│   │   └── <FY>/
│   │       ├── input/bank_statements/
│   │       └── output/
│   └── README.md
└── scripts/
    ├── run_and_verify.ps1      # 1-click pipeline runner (PowerShell)
    └── run_and_verify.sh       # 1-click pipeline runner (Bash)
```

---

## Running Tests & Linting

```bash
# Run unit tests
python -m unittest discover -s src/tax_automation/tests

# Run code style and linting (flake8)
python -m flake8 src --max-line-length=88
```