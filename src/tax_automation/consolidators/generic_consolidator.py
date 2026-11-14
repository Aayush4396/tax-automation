# -*- coding: utf-8 -*-
"""generic_consolidator.py.

Consolidates individual bank statement files (XLS, XLSX, CSV, PDF) for an entity
and Financial Year into a multi-sheet workbook using JSON consolidation maps.
"""

from __future__ import annotations
import csv
import io
from pathlib import Path
import msoffcrypto
from openpyxl import Workbook
import pandas as pd
import pdfplumber

from tax_automation.config_loader import (
    get_consolidation_map,
    resolve_password,
    resolve_input_dir,
    resolve_output_dir,
)


def decrypt_excel(filepath: Path, password: str) -> io.BytesIO:
    """Decrypts a password-protected Excel file in memory."""
    decrypted = io.BytesIO()
    with open(filepath, "rb") as f:
        file_dec = msoffcrypto.OfficeFile(f)
        file_dec.load_key(password=password)
        file_dec.decrypt(decrypted)
    decrypted.seek(0)
    return decrypted


def load_file_to_df(
    filepath: Path, password: str | None = None, source_sheet: str | int | None = None,
    delimiter: str = ",", encoding: str = "utf-8-sig"
) -> tuple[pd.DataFrame, list[list]]:
    """Loads CSV, PDF, XLS, or XLSX statements into a DataFrame,
    decrypting if necessary.
    """
    ext = filepath.suffix.lower()

    if ext == ".csv":
        with open(filepath, "r", encoding=encoding, newline="") as f:
            rows = list(csv.reader(f, delimiter=delimiter))
        df = pd.DataFrame(rows)
        return df, rows

    elif ext == ".pdf":
        with pdfplumber.open(filepath, password=password) as pdf:
            final_rows = []
            first_header = None
            width = None
            for page_number, page in enumerate(pdf.pages, 1):
                tables = page.extract_tables()
                if not tables:
                    raise ValueError(
                        f"{filepath.name}: page {page_number} has no table; "
                        "use a tabular export or a dedicated parser"
                    )
                for table in tables:
                    if not table:
                        continue
                    if width is None:
                        width = len(table[0])
                        first_header = table[0]
                        text = page.extract_text() or ""
                        final_rows.extend(
                            [line] + [""] * (width - 1)
                            for line in text.splitlines()[:5] if line.strip()
                        )
                    if any(len(row) != width for row in table):
                        raise ValueError(
                            f"{filepath.name}: inconsistent PDF table columns"
                        )
                    if (table[0] == first_header
                            and first_header in final_rows):
                        table = table[1:]
                    final_rows.extend(table)
            if width is None:
                raise ValueError(f"{filepath.name}: no tabular data found")
            return pd.DataFrame(final_rows), final_rows

    elif ext in (".xls", ".xlsx"):
        if password:
            decrypted = decrypt_excel(filepath, password)
            xl = pd.ExcelFile(decrypted)
            df = _read_excel_sheet(xl, source_sheet)
            return df, df.values.tolist()
        else:
            with open(filepath, "rb") as f:
                header = f.read(16)
            is_ole = header.startswith(b"\xd0\xcf\x11\xe0")
            engine = "xlrd" if (is_ole and ext == ".xlsx") else None
            xl = pd.ExcelFile(filepath, engine=engine)
            df = _read_excel_sheet(xl, source_sheet)
            return df, df.values.tolist()

    else:
        raise ValueError(f"Unsupported file format: {ext}")


def _read_excel_sheet(xl: pd.ExcelFile, source_sheet: str | int | None) -> pd.DataFrame:
    with xl:
        if source_sheet is None:
            if len(xl.sheet_names) != 1:
                raise ValueError(
                    "Multiple Excel worksheets: specify source_sheet"
                )
            source_sheet = xl.sheet_names[0]
        return xl.parse(source_sheet, header=None)


def consolidate_entity_statements(
    entity_id: str,
    fy: str,
    data_dir: Path | None = None,
    output_dir: Path | None = None,
) -> Path:
    """Consolidates individual bank statements for an entity into a
    multi-sheet Excel file at canonical output path.
    """
    cmap = get_consolidation_map(entity_id, fy)

    if data_dir is None:
        data_dir = resolve_input_dir(entity_id, fy, "bank_statements")

    if output_dir is None:
        output_dir = resolve_output_dir(entity_id, fy)

    output_path = output_dir / "consolidated_statements.xlsx"

    wb = Workbook()
    wb.remove(wb.active)

    files = cmap.get("files", [])
    if not files:
        raise ValueError("Consolidation map must contain a non-empty files list")
    target_names = set()
    for file_spec in files:
        filename = file_spec["filename"]
        target_sheet = file_spec["sheet_name"]
        if (not target_sheet or len(target_sheet) > 31
                or any(c in target_sheet for c in "[]:*?/\\")):
            raise ValueError(f"Invalid worksheet name: {target_sheet!r}")
        if target_sheet.casefold() in target_names:
            raise ValueError(f"Duplicate target sheet: {target_sheet}")
        target_names.add(target_sheet.casefold())
        pwd_var = file_spec.get("password_env_var")
        password = resolve_password(pwd_var) if pwd_var else None

        if pwd_var and not password:
            raise ValueError(f"Missing password environment variable: {pwd_var}")
        file_path = data_dir / filename
        if not file_path.exists():
            raise FileNotFoundError(f"Statement not found: {file_path}")

        df, _ = load_file_to_df(
            file_path, password, source_sheet=file_spec.get("source_sheet"),
            delimiter=file_spec.get("delimiter", ","),
            encoding=file_spec.get("encoding", "utf-8-sig"),
        )
        ws = wb.create_sheet(title=target_sheet)
        for r_idx, row in enumerate(df.values.tolist(), 1):
            for c_idx, val in enumerate(row, 1):
                ws.cell(
                    row=r_idx,
                    column=c_idx,
                    value=val if pd.notna(val) else "",
                )

    output_dir.mkdir(parents=True, exist_ok=True)
    wb.save(output_path)
    return output_path
