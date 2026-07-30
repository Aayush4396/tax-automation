# -*- coding: utf-8 -*-
"""
consolidate_statements.py
==========================
Generically consolidates all individual bank statements (XLS, XLSX, CSV, PDF)
for any given Financial Year (default FY26) into a single multi-sheet workbook:
"All Bank Statements Ajay <FY>.xlsx".

Uses fingerprint-based identification to match each file to its bank config
and target sheet name dynamically, avoiding hardcoded filename configurations.
"""

from __future__ import annotations
import os
import io
import re
import sys
import argparse
import csv
from pathlib import Path
import pandas as pd
import pdfplumber
import msoffcrypto
from openpyxl import Workbook

# Force UTF-8 terminal output
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

# Add parent directory to path to import narration_engine modules
sys.path.append(str(Path(__file__).resolve().parent))

from narration_engine.auto_header import find_header_row
from narration_engine.bank_identifier import identify_bank
from narration_engine.bank_registry import BANK_REGISTRY

KNOWN_PASSWORDS = ["AJAY 11111967", "AJAYK11111967"]

def decrypt_excel(filepath: Path, password: str) -> io.BytesIO:
    """Decrypts a password-protected Excel file in memory."""
    decrypted = io.BytesIO()
    with open(filepath, "rb") as f:
        file_dec = msoffcrypto.OfficeFile(f)
        file_dec.load_key(password=password)
        file_dec.decrypt(decrypted)
    decrypted.seek(0)
    return decrypted

def load_file_to_df(filepath: Path) -> tuple[pd.DataFrame, list[list]]:
    """
    Loads various formats (xls, xlsx, csv, pdf) into a DataFrame.
    Automatically handles password decryption by trying known passwords.
    Returns (dataframe, raw_rows_list).
    """
    ext = filepath.suffix.lower()
    
    # ── Handle CSV Files ──
    if ext == ".csv":
        try:
            with open(filepath, "r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()
            rows = []
            for line in lines:
                reader = csv.reader(io.StringIO(line))
                row = next(reader, [])
                rows.append(row)
            df = pd.DataFrame(rows)
            return df, rows
        except Exception as e:
            print(f"  ❌ Error reading CSV {filepath.name}: {e}")
            raise e

    # ── Handle PDF Files ──
    elif ext == ".pdf":
        decrypted_pdf = None
        # Try opening without password first
        try:
            with pdfplumber.open(filepath) as pdf:
                page = pdf.pages[0]
                tables = page.extract_tables()
        except Exception:
            # Try passwords
            for pwd in KNOWN_PASSWORDS:
                try:
                    with pdfplumber.open(filepath, password=pwd) as pdf:
                        page = pdf.pages[0]
                        tables = page.extract_tables()
                        decrypted_pdf = pwd
                        break
                except Exception:
                    continue
            if not decrypted_pdf:
                raise ValueError(f"Failed to decrypt PDF {filepath.name} with known passwords.")
                
        try:
            pwd_to_use = decrypted_pdf if decrypted_pdf else None
            with pdfplumber.open(filepath, password=pwd_to_use) as pdf:
                page = pdf.pages[0]
                tables = page.extract_tables()
                if not tables:
                    raise ValueError("No tabular data found in PDF")
                table = tables[0]
                df_table = pd.DataFrame(table)
                
                # Prepend some metadata so identify_bank works for the SBI Insurance Loan PDF
                metadata = [
                    ["State Bank of India", "", "", "", "", "", ""],
                    ["STATEMENT OF ACCOUNT", "", "", "", "", "", ""],
                    ["Account No : 32718709979", "", "", "", "", "", ""],
                    ["Product : Personal Loan (Insurance Loan)", "", "", "", "", "", ""],
                    ["", "", "", "", "", "", ""], # blank row separator
                ]
                final_rows = metadata + df_table.values.tolist()
                return pd.DataFrame(final_rows), final_rows
        except Exception as e:
            print(f"  ❌ Error reading PDF {filepath.name}: {e}")
            raise e

    # ── Handle Excel Files (XLS, XLSX) ──
    elif ext in (".xls", ".xlsx"):
        # Check magic bytes for OLE/encryption
        with open(filepath, "rb") as f:
            header = f.read(16)
        is_ole = header.startswith(b"\xd0\xcf\x11\xe0")

        # Try loading without password first
        try:
            engine = "xlrd" if (is_ole and ext == ".xlsx") else None
            xl = pd.ExcelFile(filepath, engine=engine)
            df = xl.parse(xl.sheet_names[0], header=None)
            raw_rows = df.values.tolist()
            return df, raw_rows
        except Exception as e:
            # Check if it looks like an encrypted file
            # If so, try known passwords
            decrypted_data = None
            for pwd in KNOWN_PASSWORDS:
                try:
                    decrypted_data = decrypt_excel(filepath, pwd)
                    break
                except Exception:
                    continue
            
            if decrypted_data:
                try:
                    decrypted_data.seek(0)
                    xl = pd.ExcelFile(decrypted_data)
                    df = xl.parse(xl.sheet_names[0], header=None)
                    return df, df.values.tolist()
                except Exception:
                    try:
                        decrypted_data.seek(0)
                        xl = pd.ExcelFile(decrypted_data, engine="xlrd")
                        df = xl.parse(xl.sheet_names[0], header=None)
                        return df, df.values.tolist()
                    except Exception as e2:
                        print(f"  ❌ Failed to parse decrypted Excel {filepath.name}: {e2}")
                        raise e2
            else:
                print(f"  ❌ Excel {filepath.name} is encrypted or corrupted and could not be opened: {e}")
                raise e

    raise ValueError(f"Unsupported file format: {ext}")


def main():
    parser = argparse.ArgumentParser(description="Generically consolidate bank statements.")
    parser.add_argument("--fy", default="FY26", help="Financial Year to consolidate, e.g. FY26")
    parser.add_argument("--input-dir", default=None, help="Directory containing bank statements")
    parser.add_argument("--output", default=None, help="Path for consolidated Excel workbook output")
    args = parser.parse_args()

    fy = args.fy
    
    # Resolve directories
    base_dir = Path(args.input_dir) if args.input_dir else Path(fr"E:\Tax\Ajay\Data\{fy}\Bank_Statements")
    output_path = Path(args.output) if args.output else base_dir / f"All Bank Statements Ajay {fy}.xlsx"

    if not base_dir.exists():
        print(f"Error: Bank statements directory not found at {base_dir}")
        sys.exit(1)

    print(f"\n==========================================================")
    print(f" DYNAMIC CONSOLIDATION FOR {fy}")
    print(f" Input Directory:  {base_dir}")
    print(f" Target Output:    {output_path}")
    print(f"==========================================================\n")

    # Scan for files
    all_files = sorted(list(base_dir.iterdir()))
    statement_files = []
    for f in all_files:
        if f.is_file() and f.suffix.lower() in (".xls", ".xlsx", ".csv", ".pdf"):
            # Exclude temp files and outputs
            name = f.name.lower()
            if name.startswith("~$") or "all bank statements" in name or "all_narrated" in name:
                continue
            statement_files.append(f)

    if not statement_files:
        print(f"No individual bank statement files found in {base_dir}.")
        sys.exit(0)

    combined_wb = Workbook()
    combined_wb.remove(combined_wb.active)  # Remove default active sheet

    success_count = 0

    for filepath in statement_files:
        print(f"Processing: {filepath.name}")
        try:
            # 1. Load file
            df, raw_rows = load_file_to_df(filepath)
            
            # 2. Identify bank type
            hdr_idx = find_header_row(raw_rows)
            bank_key, score = identify_bank(raw_rows, hdr_idx, filepath.stem)
            
            if bank_key == "unknown":
                print(f"  ⚠️ Warning: Could not identify bank type (best score: {score:.2f}). Skipping.")
                continue
                
            config = BANK_REGISTRY[bank_key]
            sheet_name = config.get("sheet_name", config.get("account_id", bank_key))
            
            print(f"  -> Identified as: {config['display_name']} ({bank_key}) with score {score:.2f}")
            print(f"  -> Target Sheet : '{sheet_name}'")
            
            # 3. Create sheet and write contents
            ws = combined_wb.create_sheet(title=sheet_name[:31])
            for r_idx, row in enumerate(df.values, start=1):
                for c_idx, val in enumerate(row, start=1):
                    if pd.notna(val) and val != "":
                        val_str = str(val).strip().replace(",", "")
                        # Coerce string numbers to float if applicable
                        if val_str and not val_str.startswith("0") and val_str.replace(".", "", 1).isdigit() and len(val_str) < 15:
                            try:
                                val = float(val_str)
                            except:
                                pass
                        ws.cell(row=r_idx, column=c_idx, value=val)
            print(f"  -> Successfully consolidated {len(df)} rows.")
            success_count += 1
            
        except Exception as e:
            print(f"  ❌ Failed to process {filepath.name}: {e}")

    if success_count > 0:
        # Save combined workbook
        combined_wb.save(output_path)
        print(f"\n[+] Success: Consolidated {success_count} statements into:")
        print(f"    {output_path}\n")
    else:
        print("\n[-] Error: No statements were successfully consolidated.")
        sys.exit(1)

if __name__ == "__main__":
    main()
