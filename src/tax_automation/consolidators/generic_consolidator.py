# -*- coding: utf-8 -*-
"""generic_consolidator.py.

Consolidates individual bank statement files (XLS, XLSX, CSV, PDF) for an entity
and Financial Year into a multi-sheet workbook using JSON consolidation maps.
"""

from __future__ import annotations
import csv
import io
import json
import re
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
    resolve_entity_bank_registry,
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
    filepath: Path,
    password: str | None = None,
    source_sheet: str | int | None = None,
    delimiter: str = ",",
    encoding: str = "utf-8-sig",
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
                            for line in text.splitlines()[:5]
                            if line.strip()
                        )
                    if any(len(row) != width for row in table):
                        raise ValueError(
                            f"{filepath.name}: inconsistent PDF table columns"
                        )
                    if table[0] == first_header and first_header in final_rows:
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
                raise ValueError("Multiple Excel worksheets: specify source_sheet")
            source_sheet = xl.sheet_names[0]
        return xl.parse(source_sheet, header=None)


def _excel_source(filepath, password):
    if password:
        return pd.ExcelFile(decrypt_excel(filepath, password))
    with open(filepath, "rb") as stream:
        is_ole = stream.read(16).startswith(b"\xd0\xcf\x11\xe0")
    engine = "xlrd" if is_ole and filepath.suffix.lower() == ".xlsx" else None
    return pd.ExcelFile(filepath, engine=engine)


def load_statement_sheets(filepath, password=None, spec=None):
    """Inventory every sheet, including explicitly excluded and hidden sheets."""
    spec = spec or {}
    if filepath.suffix.lower() not in (".xls", ".xlsx"):
        df, _ = load_file_to_df(
            filepath,
            password,
            delimiter=spec.get("delimiter", ","),
            encoding=spec.get("encoding", "utf-8-sig"),
        )
        return [(None, df, None)]
    with _excel_source(filepath, password) as xl:
        selected = spec.get("source_sheet")
        if isinstance(selected, int):
            if not 0 <= selected < len(xl.sheet_names):
                raise ValueError(f"{filepath.name}: source_sheet index out of range")
            selected = xl.sheet_names[selected]
        if selected is not None and selected not in xl.sheet_names:
            raise ValueError(f"{filepath.name}: unknown source_sheet {selected}")
        if set(spec.get("sheet_map", {})) - set(xl.sheet_names):
            raise ValueError(f"{filepath.name}: unknown sheet_map source")
        excluded = set(spec.get("exclude_sheets", []))
        if excluded - set(xl.sheet_names):
            raise ValueError(f"{filepath.name}: unknown exclude_sheets")
        result = []
        for name in xl.sheet_names:
            if name in excluded:
                result.append((name, None, "explicitly excluded"))
            elif selected is not None and name != selected:
                result.append((name, None, "outside explicit source_sheet selection"))
            else:
                df = xl.parse(name, header=None)
                if df.dropna(how="all").empty:
                    result.append((name, None, "empty worksheet"))
                else:
                    result.append((name, df, None))
        return result


def _target_sheet(name, df, spec, registry, selected_count):
    explicit = spec.get("sheet_map", {}).get(name)
    if explicit:
        return explicit
    if selected_count == 1 and spec.get("sheet_name"):
        return spec["sheet_name"]
    normalized = re.sub(r"[^a-z0-9]", "", (name or "").lower())
    exact = [
        cfg["sheet_name"]
        for cfg in registry.values()
        if name
        and name.casefold()
        in {
            str(v).casefold()
            for v in [cfg["sheet_name"], *cfg.get("sheet_aliases", [])]
        }
    ]
    if len(exact) == 1:
        return exact[0]
    banks = [
        cfg["sheet_name"]
        for cfg in registry.values()
        if normalized in {cfg.get("bank_type"), cfg.get("bank_type", "") + "bank"}
    ]
    if len(banks) == 1:
        return banks[0]
    from tax_automation.core.auto_header import find_header_row
    from tax_automation.core.bank_identifier import identify_bank

    rows = df.values.tolist()
    key, _ = identify_bank(rows, find_header_row(rows), registry, name or "")
    if key == "unknown":
        raise ValueError(f"Cannot resolve source sheet {name!r}; add sheet_map")
    return registry[key]["sheet_name"]


def consolidate_entity_statements(
    entity_id: str,
    fy: str,
    data_dir: Path | None = None,
    output_dir: Path | None = None,
) -> Path:
    """Import all workbook sheets by default; never silently select the first."""
    cmap = get_consolidation_map(entity_id, fy)
    data_dir = data_dir or resolve_input_dir(entity_id, fy, "bank_statements")
    output_dir = output_dir or resolve_output_dir(entity_id, fy)
    output_path = output_dir / "consolidated_statements.xlsx"
    files = cmap.get("files", [])
    if not files:
        raise ValueError("Consolidation map must contain a non-empty files list")
    wb = Workbook()
    wb.remove(wb.active)
    target_names, manifest = set(), []
    registry = None
    for spec in files:
        path = data_dir / spec["filename"]
        if not path.exists():
            raise FileNotFoundError(f"Statement not found: {path}")
        pwd_var = spec.get("password_env_var")
        password = resolve_password(pwd_var) if pwd_var else None
        if pwd_var and not password:
            raise ValueError(f"Missing password environment variable: {pwd_var}")
        sheets = load_statement_sheets(path, password, spec)
        selected_count = sum(df is not None for _, df, _ in sheets)
        for name, df, reason in sheets:
            entry = {"file": path.name, "source_sheet": name}
            if reason:
                manifest.append({**entry, "status": "skipped", "reason": reason})
                continue
            if registry is None and not (
                selected_count == 1 and spec.get("sheet_name")
            ):
                registry = resolve_entity_bank_registry(entity_id)
            target = _target_sheet(name, df, spec, registry or {}, selected_count)
            if not target or len(target) > 31 or any(c in target for c in "[]:*?/\\"):
                raise ValueError(f"Invalid worksheet name: {target!r}")
            if target.casefold() in target_names:
                raise ValueError(
                    f"Duplicate target sheet {target}: {path.name}/{name}; "
                    "select one authoritative statement per account"
                )
            target_names.add(target.casefold())
            ws = wb.create_sheet(title=target)
            for row in df.values.tolist():
                ws.append([v if pd.notna(v) else None for v in row])
            manifest.append(
                {
                    **entry,
                    "target_sheet": target,
                    "status": "imported",
                    "source_rows": len(df),
                }
            )
    if not wb.sheetnames:
        raise ValueError("No non-empty statement sheets selected")
    output_dir.mkdir(parents=True, exist_ok=True)
    wb.save(output_path)
    (output_dir / "consolidation_manifest.json").write_text(
        json.dumps({"entity": entity_id, "fy": fy, "sheets": manifest}, indent=2),
        encoding="utf-8",
    )
    return output_path
