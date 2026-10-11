# -*- coding: utf-8 -*-
"""check_contras.py.

Verifies whether all identified self-transfers (Contras) in bank statements
have corresponding matching contra entries across other bank accounts.
"""

from __future__ import annotations
import argparse
import io
from pathlib import Path
import sys
from openpyxl import load_workbook

from tax_automation.config_loader import (
    get_entity_config,
    resolve_output_dir,
    REPO_ROOT,
)


def verify_contras(entity_id: str, fy: str, file_path: Path | None = None) -> bool:
    """Verifies contra symmetry for an entity and FY."""
    config = get_entity_config(entity_id)
    output_sheet_names = set(config.get("output_sheet_names", []))
    entity_dir_name = entity_id.title()

    if file_path is None:
        file_path = resolve_output_dir(entity_id, fy) / "narrated_ledger.xlsx"
        if not file_path.exists():
            legacy_path = (
                REPO_ROOT
                / "data"
                / entity_dir_name
                / "Generated Data"
                / fy
                / f"{entity_dir_name}_Consolidated_Bank_Ledger_{fy}.xlsx"
            )
            if legacy_path.exists():
                file_path = legacy_path

    if not file_path.exists():
        print(f"Error: Ledger file not found at {file_path}")
        return False

    print(f"Verifying contras for {entity_id.title()} ({fy}) in: {file_path}")
    wb = load_workbook(file_path, data_only=True)
    sheet_names = [s for s in wb.sheetnames if s not in output_sheet_names]

    contras = []
    for sheet in sheet_names:
        ws = wb[sheet]
        rows = list(ws.iter_rows(values_only=True))
        if len(rows) < 2:
            continue

        header = [str(c).strip().lower() if c else "" for c in rows[0]]
        try:
            date_idx = header.index("date")
            part_idx = header.index("particulars")
            dr_idx = header.index("debit")
            cr_idx = header.index("credit")
            lbl_idx = header.index("narration label")
        except ValueError:
            continue

        for r in rows[1:]:
            lbl = str(r[lbl_idx] or "")
            if lbl.startswith("Contra"):
                dr_val = float(r[dr_idx] or 0.0)
                cr_val = float(r[cr_idx] or 0.0)
                contras.append(
                    {
                        "sheet": sheet,
                        "date": r[date_idx],
                        "particulars": r[part_idx],
                        "dr": dr_val,
                        "cr": cr_val,
                        "label": lbl,
                    }
                )

    total_dr = sum(c["dr"] for c in contras)
    total_cr = sum(c["cr"] for c in contras)
    diff = abs(total_dr - total_cr)

    print(f"Total Identified Contras: {len(contras)}")
    print(f"Total Contra Debits:      {total_dr:,.2f}")
    print(f"Total Contra Credits:     {total_cr:,.2f}")
    print(f"Difference:               {diff:,.2f}")

    if diff < 1.0:
        print("[PASS] Contras are symmetric and balanced.")
        return True
    else:
        print(f"[WARN] Imbalance of {diff:,.2f} detected across Contras.")
        return False


def main():
    if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
        sys.stdout = io.TextIOWrapper(
            sys.stdout.buffer, encoding="utf-8", errors="replace"
        )
    parser = argparse.ArgumentParser(
        description="Verify contra balance across accounts."
    )
    parser.add_argument("--entity", default="aayush", help="Entity profile ID")
    parser.add_argument("--fy", default="FY26", help="Financial year")
    parser.add_argument("--file", help="Explicit path to output ledger")
    args = parser.parse_args()

    file_p = Path(args.file) if args.file else None
    verify_contras(args.entity, args.fy, file_p)


if __name__ == "__main__":
    main()
