# -*- coding: utf-8 -*-
"""parse_narration_stats.py.

Parses generated Excel ledger and displays classification confidence statistics.
"""

from __future__ import annotations
import argparse
import io
from pathlib import Path
import sys
import pandas as pd

from tax_automation.config_loader import resolve_output_dir, REPO_ROOT


def get_narration_stats(filepath: Path, fy: str):
    if not filepath.exists():
        print(f"File not found: {filepath}")
        return

    xl = pd.ExcelFile(filepath)
    exclude = {"Conso", "For Tally", "Bank Summary", "Monthly Pivot", "Guidelines"}
    sheet_names = [s for s in xl.sheetnames if s not in exclude]

    dfs = []
    for s in sheet_names:
        df = xl.parse(s)
        dfs.append(df)

    if not dfs:
        return
    full_df = pd.concat(dfs, ignore_index=True)
    total = len(full_df)

    # Check for confidence column
    if "Confidence" in full_df.columns:
        high = len(full_df[full_df["Confidence"] >= 0.85])
        med = len(
            full_df[
                (full_df["Confidence"] >= 0.60) & (full_df["Confidence"] < 0.85)
            ]
        )
        low = len(full_df[full_df["Confidence"] < 0.60])
        print(f"\nNarration Stats for {fy} (Total Transactions: {total}):")
        print(f"  High Confidence (>= 85%): {high} ({high/total*100:.1f}%)")
        print(f"  Med  Confidence (60-84%): {med} ({med/total*100:.1f}%)")
        print(f"  Low  Confidence (< 60%):  {low} ({low/total*100:.1f}%)")


def main():
    if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
        sys.stdout = io.TextIOWrapper(
            sys.stdout.buffer, encoding="utf-8", errors="replace"
        )
    parser = argparse.ArgumentParser(description="Parse narration statistics.")
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

    get_narration_stats(p, args.fy)


if __name__ == "__main__":
    main()
