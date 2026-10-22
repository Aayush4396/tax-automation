# -*- coding: utf-8 -*-
"""check_contras.py.

Verifies whether all identified self-transfers (Contras) in bank statements
have corresponding matching contra entries across other bank accounts.
"""

from __future__ import annotations
from pathlib import Path
from openpyxl import load_workbook

from tax_automation.config_loader import get_entity_config, resolve_output_dir


def verify_contras(entity_id: str, fy: str, file_path: Path | None = None) -> bool:
    """Verifies contra symmetry for an entity and FY."""
    config = get_entity_config(entity_id)
    output_sheet_names = set(config.get("output_sheet_names", []))

    if file_path is None:
        file_path = resolve_output_dir(entity_id, fy) / "narrated_ledger.xlsx"

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

        h_idx = None
        for i in range(min(10, len(rows))):
            r_str = [str(c).strip().lower() if c is not None else "" for c in rows[i]]
            if any("particular" in c for c in r_str) and any(
                c in ("dr", "debit") for c in r_str
            ):
                h_idx = i
                break
        if h_idx is None:
            continue

        header = [str(c).strip().lower() if c is not None else "" for c in rows[h_idx]]
        date_idx = next((i for i, c in enumerate(header) if "date" in c), None)
        part_idx = next((i for i, c in enumerate(header) if "particular" in c), None)
        dr_idx = next((i for i, c in enumerate(header) if c in ("dr", "debit")), None)
        cr_idx = next((i for i, c in enumerate(header) if c in ("cr", "credit")), None)
        lbl_idx = next(
            (i for i, c in enumerate(header) if "narration" in c or "label" in c),
            None,
        )

        if dr_idx is None or cr_idx is None or lbl_idx is None:
            continue

        for r in rows[h_idx + 1 :]:
            lbl = str(r[lbl_idx] or "")
            if lbl.startswith("Contra"):
                dr_val = float(r[dr_idx] or 0.0)
                cr_val = float(r[cr_idx] or 0.0)
                contras.append(
                    {
                        "sheet": sheet,
                        "date": r[date_idx] if date_idx is not None else None,
                        "particulars": r[part_idx] if part_idx is not None else "",
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
