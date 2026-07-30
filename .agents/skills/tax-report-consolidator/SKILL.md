---
name: tax-report-consolidator
description: Consolidates multi-format bank statement files (XLS, XLSX, CSV, PDF) into single multi-sheet workbooks using JSON consolidation maps and encrypted file passwords from environment variables.
---

# Tax Report Consolidator Skill

## Objective
Consolidate individual bank statement files (XLS, XLSX, CSV, PDF) for an entity profile and Financial Year into a single multi-sheet Excel workbook.

---

## Execution Steps

### Step 1: Consolidation Map Lookup
1. Load consolidation mapping configuration from `config/consolidation/<entity>_<fy>.json`.
2. Parse target input files, target sheet names, and password environment variable keys.
3. Load credentials from `.env` file for encrypted statement files.

### Step 2: File Ingestion & Decryption
1. Scan source directory `data/<entity>/Data/<FY>/Bank_Statements/` (or equivalent).
2. Decrypt password-protected Excel/PDF files in-memory using `msoffcrypto-tool` and `pdfplumber`.
3. Parse tabular data into unified Pandas DataFrames with standardized schema.

### Step 3: Multi-Sheet Workbook Generation
1. Write each bank's statement data to its designated worksheet (`HDFC 5930`, `AXIS 3167`, `BOI 6699`, `SBI CA`, etc.).
2. Apply header formatting and auto-column width calculations.
3. Save output workbook to `data/<entity>/Data/<FY>/Bank_Statements/All Bank Statements <Entity> <FY>.xlsx`.
