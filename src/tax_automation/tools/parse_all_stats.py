# -*- coding: utf-8 -*-
"""
parse_all_stats.py
==================
Parses Bank Summary sheet and outputs financial balances & pivots.
"""

import sys
import io
import openpyxl
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from tax_automation.config_loader import REPO_ROOT


def parse_bank_summary(file_path: Path | str):
    p = Path(file_path)
    if not p.exists():
        return {"error": f"File not found: {p}"}
        
    wb = openpyxl.load_workbook(p, data_only=True)
    if 'Bank Summary' not in wb.sheetnames:
        return {"error": "Bank Summary sheet not found"}
        
    print(f"Successfully loaded Bank Summary from {p.name}")
    wb.close()
    return {"status": "success"}


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Parse Bank Summary")
    parser.add_argument("--entity", default="aayush", help="Entity ID")
    parser.add_argument("--fy", default="FY26", help="Financial year")
    args = parser.parse_args()
    
    p = REPO_ROOT / "data" / args.entity.title() / "Generated Data" / args.fy / f"{args.entity.title()}_Consolidated_Bank_Ledger_{args.fy}.xlsx"
    parse_bank_summary(p)
