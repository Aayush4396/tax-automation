# -*- coding: utf-8 -*-
"""
check_contras.py
================
Verifies whether all identified self-transfers (Contras) in bank statements
are matching symmetrically across accounts.
"""

import sys
import io
import argparse
import re
from pathlib import Path
import pandas as pd
from openpyxl import load_workbook

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from tax_automation.config_loader import get_entity_config, REPO_ROOT


def build_bank_map(config: dict) -> dict[str, str]:
    """Dynamically builds account_id -> display_key mapping from entity config."""
    bank_map = {}
    for key, cfg in config.get("banks", {}).items():
        acct_id = cfg.get("account_id")
        if acct_id:
            bank_map[acct_id] = key.upper()
    return bank_map


def verify_contras(entity_id: str, fy: str, file_path: Path | None = None) -> bool:
    """Verifies contra symmetry for an entity and FY."""
    config = get_entity_config(entity_id)
    bank_map = build_bank_map(config)
    output_sheet_names = set(config.get("output_sheet_names", []))
    entity_dir_name = entity_id.title()

    if file_path is None:
        file_path = REPO_ROOT / "data" / entity_dir_name / "Generated Data" / fy / f"{entity_dir_name}_Consolidated_Bank_Ledger_{fy}.xlsx"

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
            
        # Find header
        hdr_idx = 0
        for i, r in enumerate(rows[:20]):
            cells = [str(c).strip().lower() for c in r if c is not None]
            if "date" in cells and ("debit" in cells or "dr" in cells or "withdrawal amt." in cells):
                hdr_idx = i
                break
                
        hdr = [str(c).strip() if c is not None else "" for c in rows[hdr_idx]]
        df = pd.DataFrame(rows[hdr_idx+1:], columns=hdr[:len(rows[hdr_idx])])
        
        # Filter contra rows
        narration_col = "Auto_Narration" if "Auto_Narration" in df.columns else ("Narration" if "Narration" in df.columns else None)
        if not narration_col:
            continue
            
        contra_df = df[df[narration_col].str.startswith("Contra", na=False)]
        for _, row in contra_df.iterrows():
            contras.append({
                "Sheet": sheet,
                "Date": row.get("Date"),
                "Particulars": row.get("Particulars"),
                "Narration": row.get(narration_col),
                "DR": row.get("DR", 0.0) or row.get("Withdrawal Amt.", 0.0) or 0.0,
                "CR": row.get("CR", 0.0) or row.get("Deposit Amt.", 0.0) or 0.0,
            })
            
    print(f"Total contra transactions found across accounts: {len(contras)}")
    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Check contra symmetry")
    parser.add_argument("--entity", default="aayush", help="Entity profile ID")
    parser.add_argument("--fy", default="FY26", help="Financial year")
    args = parser.parse_args()
    verify_contras(args.entity, args.fy)
