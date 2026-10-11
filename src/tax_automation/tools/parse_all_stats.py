# -*- coding: utf-8 -*-
"""parse_all_stats.py.

Parses Bank Summary sheet of the generated master Excel ledger.
"""

from __future__ import annotations
import argparse
import io
from pathlib import Path
import sys
import pandas as pd

from tax_automation.config_loader import resolve_output_dir, REPO_ROOT


def parse_bank_summary(filepath: Path):
    if not filepath.exists():
        print(f"File not found: {filepath}")
        return

    xl = pd.ExcelFile(filepath)
    if "Bank Summary" not in xl.sheetnames:
        print("Bank Summary sheet not found")
        return

    df = xl.parse("Bank Summary", skiprows=4)
    print("\n--- Bank Summary Sheet ---")
    print(df.to_string())


def main():
    if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
        sys.stdout = io.TextIOWrapper(
            sys.stdout.buffer, encoding="utf-8", errors="replace"
        )
    parser = argparse.ArgumentParser(description="Parse bank summary stats.")
    parser.add_argument("--entity", default="aayush", help="Entity ID")
    parser.add_argument("--fy", default="FY26", help="Financial year")
    parser.add_argument("--file", help="Explicit file path")
    args = parser.parse_args()

    if args.file:
        p = Path(args.file)
    else:
        p = resolve_output_dir(args.entity, args.fy) / "narrated_ledger.xlsx"
        if not p.exists():
            legacy_p = (
                REPO_ROOT
                / "data"
                / args.entity.title()
                / "Generated Data"
                / args.fy
                / f"{args.entity.title()}_Consolidated_Bank_Ledger_{args.fy}.xlsx"
            )
            if legacy_p.exists():
                p = legacy_p

    parse_bank_summary(p)


if __name__ == "__main__":
    main()
