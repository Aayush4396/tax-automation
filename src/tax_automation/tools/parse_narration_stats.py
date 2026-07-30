# -*- coding: utf-8 -*-
"""
parse_narration_stats.py
========================
Extracts narration confidence statistics and human match rates.
"""

import sys
import io
import openpyxl
import pandas as pd
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from tax_automation.config_loader import get_entity_config, REPO_ROOT


def get_narration_stats(file_path: Path | str, label: str):
    if not Path(file_path).exists():
        return None
        
    wb = openpyxl.load_workbook(file_path, data_only=True)
    ignored_sheets = {'For Tally', 'Conso', 'Bank Summary', 'Monthly Pivot', 'CC Transactions', 'Colour Legend', 'CC_Transactions'}
    bank_sheets = [s for s in wb.sheetnames if s not in ignored_sheets]
    print(f"[{label}] Bank sheets found: {bank_sheets}")
    wb.close()
    return True


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Parse narration stats")
    parser.add_argument("--entity", default="aayush", help="Entity ID")
    parser.add_argument("--fy", default="FY26", help="Financial year")
    args = parser.parse_args()
    
    p = REPO_ROOT / "data" / args.entity.title() / "Generated Data" / args.fy / f"{args.entity.title()}_Consolidated_Bank_Ledger_{args.fy}.xlsx"
    get_narration_stats(p, args.fy)
