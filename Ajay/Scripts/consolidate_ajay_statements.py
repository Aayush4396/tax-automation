# -*- coding: utf-8 -*-
"""
consolidate_ajay_statements.py
==============================
Consolidates all individual bank statements for Ajay Gupta FY26
into a single multi-sheet workbook "All Bank Statements Ajay FY26.xlsx".
Handles decryption of password-protected files in-memory using msoffcrypto.
"""

import os
import io
import re
import pandas as pd
import pdfplumber
import msoffcrypto
from openpyxl import Workbook

# Directory paths
base_dir = r"E:\Tax\Ajay\Data\FY26\Bank_Statements"
output_path = r"E:\Tax\Ajay\Data\FY26\Bank_Statements\All Bank Statements Ajay FY26.xlsx"

# Files and their target sheet names
files_mapping = [
    # (filename, target_sheet_name, password)
    ("Ajay Acct_Statement_XXXXXXXX5930_14042026.xls", "HDFC 5930", None),
    ("Ajay Axis Saving statement.xls", "AXIS 3167", None),
    ("Ajay Bank of India Kota Statement1777469280115_____ 6699.csv", "BOI 6699", None),
    ("Ajay Current account account SBI Password AJAY 11111967.xlsx", "SBI CA", "AJAY 11111967"),
    ("Ajay Kota Saving account SBI Password AJAY 11111967.xlsx", "SBI SB Kota", "AJAY 11111967"),
    ("Ajay Saving account SBI Password AJAY 11111967.xlsx", "SBI SB Nsk", "AJAY 11111967"),
    ("Ajay rawatbhata Saving account SBI Password AJAY 11111967.xlsx", "SBI SB Rawatbhata", "AJAY 11111967"),
    ("SBI Insurance loan account Nashik Password AJAYK11111967.pdf", "SBI Insurance Loan", "AJAYK11111967"),
]

def decrypt_excel(filepath, password):
    """Decrypts a password-protected Excel file in memory."""
    decrypted = io.BytesIO()
    with open(filepath, "rb") as f:
        file_dec = msoffcrypto.OfficeFile(f)
        file_dec.load_key(password=password)
        file_dec.decrypt(decrypted)
    decrypted.seek(0)
    return decrypted

def load_file_to_df(filepath, password=None):
    """Loads various file formats (xls, xlsx, csv, pdf) into a DataFrame, decrypting if necessary."""
    ext = os.path.splitext(filepath)[1].lower()
    
    # Check magic bytes for OLE (decrypted Excel might need xlrd)
    with open(filepath, "rb") as f:
        header = f.read(16)
    is_ole = header.startswith(b"\xd0\xcf\x11\xe0")

    if ext in (".xlsx", ".xls"):
        if password:
            try:
                decrypted = decrypt_excel(filepath, password)
                # Try reading decrypted file
                try:
                    xl = pd.ExcelFile(decrypted)
                except Exception:
                    decrypted.seek(0)
                    xl = pd.ExcelFile(decrypted, engine="xlrd")
                return xl.parse(xl.sheet_names[0], header=None)
            except Exception as e:
                print(f"  Error decrypting Excel {os.path.basename(filepath)}: {e}")
                raise e
        else:
            # Not password protected
            try:
                if is_ole and ext == ".xlsx":
                    # Excel 97-2003 renamed to XLSX
                    xl = pd.ExcelFile(filepath, engine="xlrd")
                else:
                    xl = pd.ExcelFile(filepath)
                return xl.parse(xl.sheet_names[0], header=None)
            except Exception as e:
                print(f"  Error reading Excel {os.path.basename(filepath)}: {e}")
                raise e
                
    elif ext == ".csv":
        # Check if it has BOI metadata
        try:
            with open(filepath, "r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()
            
            # Create a 2D list representing rows
            rows = []
            for line in lines:
                # Clean up lines and split by comma, respecting quotes
                # Let's use csv module to parse correctly
                import csv
                reader = csv.reader(io.StringIO(line))
                row = next(reader, [])
                rows.append(row)
            return pd.DataFrame(rows)
        except Exception as e:
            print(f"  Error reading CSV {os.path.basename(filepath)}: {e}")
            raise e
            
    elif ext == ".pdf":
        # Parse PDF using pdfplumber and format as a standard table
        try:
            with pdfplumber.open(filepath, password=password) as pdf:
                page = pdf.pages[0]
                tables = page.extract_tables()
                if not tables:
                    raise ValueError("No tables found in PDF")
                table = tables[0]
                
                # Create a DataFrame
                df_table = pd.DataFrame(table)
                
                # Prepend some metadata at the top so identify_bank works!
                metadata = [
                    ["State Bank of India", "", "", "", "", "", ""],
                    ["STATEMENT OF ACCOUNT", "", "", "", "", "", ""],
                    ["Account No : 32718709979", "", "", "", "", "", ""],
                    ["Product : Personal Loan (Insurance Loan)", "", "", "", "", "", ""],
                    ["", "", "", "", "", "", ""], # blank row separator
                ]
                
                # Combine metadata and table
                final_rows = metadata + df_table.values.tolist()
                return pd.DataFrame(final_rows)
        except Exception as e:
            print(f"  Error reading PDF {os.path.basename(filepath)}: {e}")
            raise e

    raise ValueError(f"Unsupported extension: {ext}")

def main():
    print("Consolidating Ajay Gupta's FY26 Bank Statements...")
    combined_wb = Workbook()
    # Remove default active sheet
    combined_wb.remove(combined_wb.active)

    for filename, sheet_name, password in files_mapping:
        filepath = os.path.join(base_dir, filename)
        print(f"Processing: {filename} -> sheet '{sheet_name}'")
        
        if not os.path.exists(filepath):
            print(f"  ⚠️ Warning: File does not exist at {filepath}")
            continue

        try:
            df = load_file_to_df(filepath, password)
            
            # Create a sheet and write cell values
            ws = combined_wb.create_sheet(title=sheet_name)
            for r_idx, row in enumerate(df.values, start=1):
                for c_idx, val in enumerate(row, start=1):
                    # Clean pandas nan or None
                    if pd.notna(val) and val != "":
                        # Coerce string numbers to float if applicable
                        val_str = str(val).strip().replace(",", "")
                        # Try parsing as float if it's a numeric amount
                        # (But ignore dates or reference numbers starting with 0)
                        if val_str and not val_str.startswith("0") and val_str.replace(".", "", 1).isdigit() and len(val_str) < 15:
                            try:
                                val = float(val_str)
                            except:
                                pass
                        ws.cell(row=r_idx, column=c_idx, value=val)
            print(f"  Successfully wrote {len(df)} rows to sheet '{sheet_name}'")
        except Exception as e:
            print(f"  ❌ Failed to process {filename}: {e}")

    combined_wb.save(output_path)
    print(f"\nSaved consolidated workbook to: {output_path}")

if __name__ == "__main__":
    main()
