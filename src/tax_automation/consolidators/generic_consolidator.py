# -*- coding: utf-8 -*-
"""
generic_consolidator.py
========================
Consolidates individual bank statement files (XLS, XLSX, CSV, PDF) for an entity
and Financial Year into a multi-sheet workbook using JSON consolidation maps.
"""

from __future__ import annotations
import os
import io
import re
import csv
from pathlib import Path
import pandas as pd
import pdfplumber
import msoffcrypto
from openpyxl import Workbook

from tax_automation.config_loader import get_consolidation_map, resolve_password, REPO_ROOT


def decrypt_excel(filepath: Path, password: str) -> io.BytesIO:
    """Decrypts a password-protected Excel file in memory."""
    decrypted = io.BytesIO()
    with open(filepath, "rb") as f:
        file_dec = msoffcrypto.OfficeFile(f)
        file_dec.load_key(password=password)
        file_dec.decrypt(decrypted)
    decrypted.seek(0)
    return decrypted


def load_file_to_df(filepath: Path, password: str | None = None) -> tuple[pd.DataFrame, list[list]]:
    """Loads CSV, PDF, XLS, or XLSX statements into a DataFrame, decrypting if necessary."""
    ext = filepath.suffix.lower()

    if ext == ".csv":
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
        rows = []
        for line in lines:
            reader = csv.reader(io.StringIO(line))
            row = next(reader, [])
            rows.append(row)
        df = pd.DataFrame(rows)
        return df, rows

    elif ext == ".pdf":
        with pdfplumber.open(filepath, password=password) as pdf:
            page = pdf.pages[0]
            tables = page.extract_tables()
            if not tables:
                raise ValueError("No tabular data found in PDF")
            df_table = pd.DataFrame(tables[0])
            metadata = [
                ["State Bank of India", "", "", "", "", "", ""],
                ["STATEMENT OF ACCOUNT", "", "", "", "", "", ""],
                ["", "", "", "", "", "", ""],
            ]
            final_rows = metadata + df_table.values.tolist()
            return pd.DataFrame(final_rows), final_rows

    elif ext in (".xls", ".xlsx"):
        if password:
            decrypted = decrypt_excel(filepath, password)
            xl = pd.ExcelFile(decrypted)
            df = xl.parse(xl.sheet_names[0], header=None)
            return df, df.values.tolist()
        else:
            with open(filepath, "rb") as f:
                header = f.read(16)
            is_ole = header.startswith(b"\xd0\xcf\x11\xe0")
            engine = "xlrd" if (is_ole and ext == ".xlsx") else None
            xl = pd.ExcelFile(filepath, engine=engine)
            df = xl.parse(xl.sheet_names[0], header=None)
            return df, df.values.tolist()

    else:
        raise ValueError(f"Unsupported file format: {ext}")


def consolidate_entity_statements(entity_id: str, fy: str, data_dir: Path | None = None) -> Path:
    """Consolidates individual bank statements for an entity into a multi-sheet Excel file."""
    cmap = get_consolidation_map(entity_id, fy)
    
    if data_dir is None:
        candidates = [
            REPO_ROOT / "data" / entity_id.title() / "Data" / fy / "Bank_Statements",
            REPO_ROOT / entity_id.title() / "Data" / fy / "Bank_Statements",
            REPO_ROOT / entity_id.title() / "Bank Statements" / fy,
        ]
        data_dir = next((c for c in candidates if c.exists() and any(c.iterdir())), candidates[0])
    
    output_filename = cmap.get("output_filename", f"All Bank Statements {entity_id.title()} {fy}.xlsx")
    output_path = data_dir / output_filename
    
    wb = Workbook()
    # Keep initial sheet and rename or track
    sheets_created = 0

    for file_spec in cmap.get("files", []):
        filename = file_spec["filename"]
        target_sheet = file_spec["sheet_name"]
        pwd_var = file_spec.get("password_env_var")
        password = resolve_password(pwd_var) if pwd_var else None
        
        file_path = data_dir / filename
        if not file_path.exists():
            print(f"Warning: File not found {file_path}")
            continue
            
        df, _ = load_file_to_df(file_path, password)
        ws = wb.create_sheet(title=target_sheet)
        sheets_created += 1
        for r_idx, row in enumerate(df.values.tolist(), 1):
            for c_idx, val in enumerate(row, 1):
                ws.cell(row=r_idx, column=c_idx, value=val if pd.notna(val) else "")

    if "Sheet" in wb.sheetnames:
        wb.remove(wb["Sheet"])

    data_dir.mkdir(parents=True, exist_ok=True)
    wb.save(output_path)
    return output_path
