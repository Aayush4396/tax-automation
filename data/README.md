# Data Directory Structure

This directory holds statement inputs and generated outputs for all taxpayer entity profiles.
Actual financial files (`.xlsx`, `.xls`, `.pdf`, `.csv`) are ignored by `.gitignore` for privacy and security.

## Layout Specification

```text
data/
├── <entity_id>/
│   ├── <FY>/                    # e.g., FY26, FY25, FY24
│   │   ├── input/
│   │   │   ├── bank_statements/ # Raw bank statement files (PDF, XLS, XLSX, CSV)
│   │   │   ├── advanced_tax/    # Advance tax receipts and calculations
│   │   │   ├── capital_gains/   # Capital gains schedules & reports
│   │   │   └── equity_related/  # Broker ledgers & trade books
│   │   └── output/
│   │       ├── consolidated_statements.xlsx  # Multi-sheet consolidated statement
│   │       └── narrated_ledger.xlsx         # Master categorized Excel ledger
│   └── credit_card_statements/  # Credit card statements (PDF, CSV)
```

## Adding a New Entity

To onboard a new entity and automatically create their directory structure:

```bash
python -m tax_automation init-entity --entity <entity_id> --name "<Full Name>" --fy FY26
```

Then copy bank statements into `data/<entity_id>/<FY>/input/bank_statements/` and run:

```bash
python -m tax_automation consolidate --entity <entity_id> --fy <FY>
python -m tax_automation process --entity <entity_id> --fy <FY>
```
