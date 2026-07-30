# -*- coding: utf-8 -*-
r"""
extract_cc_statements_to_excel.py
==================================
One-time PDF extraction script.

Extracts all credit card statement PDFs to a cached Excel file.
This avoids re-parsing PDFs every time the narration script runs.

Usage:
    python extract_cc_statements_to_excel.py --fy FY26

Output:
    e:\Tax\Aayush\Generated Data\<FY>\CC_Statements_Cache_<FY>.xlsx
"""

from __future__ import annotations
import sys
import io
import argparse
import logging
from datetime import datetime
from pathlib import Path

# Force UTF-8 output on Windows
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

import pandas as pd

# Add scripts folder to path for imports
sys.path.insert(0, str(Path(__file__).parent))
from narration_engine.parse_cc import parse_all_statements

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)-8s | %(message)s"
)

def extract_and_cache(fy: str = "FY26", cc_dir_path: Path | None = None) -> Path:
    """
    Extract all CC statement PDFs and save to Excel cache.
    
    Parameters
    ----------
    fy : str
        Fiscal year (e.g., "FY25", "FY26")
    cc_dir_path : Path, optional
        Path to credit card statements directory
    
    Returns
    -------
    cache_path : Path
        Path to the generated cache Excel file
    """
    
    # Map FY to date range
    fy_map = {
        "FY25": (datetime(2024, 4, 1), datetime(2025, 3, 31)),
        "FY26": (datetime(2025, 4, 1), datetime(2026, 3, 31)),
    }
    
    if fy not in fy_map:
        raise ValueError(f"Unknown FY: {fy}. Expected one of {list(fy_map.keys())}")
    
    fy_start, fy_end = fy_map[fy]
    cc_dir = cc_dir_path or Path(r"E:\Tax\Aayush\credit_card_statements")
    output_dir = Path(r"E:\Tax\Aayush\Generated Data") / fy
    output_dir.mkdir(parents=True, exist_ok=True)
    
    cache_path = output_dir / f"CC_Statements_Cache_{fy}.xlsx"
    
    print(f"=== CC STATEMENT EXTRACTION CACHE ({fy}) ===\n")
    print(f"PDF Directory : {cc_dir}")
    print(f"FY Range      : {fy_start.date()} → {fy_end.date()}")
    print(f"Cache Output  : {cache_path}\n")
    
    # Parse all PDFs
    print("Parsing PDF statements...")
    cc_df, metas = parse_all_statements(cc_dir, fy_start, fy_end)
    
    print(f"  ✓ {len(metas)} statements loaded")
    print(f"  ✓ {len(cc_df)} spend transactions in {fy}\n")
    
    # Save to Excel with multiple sheets
    print("Writing Excel cache...")
    
    with pd.ExcelWriter(cache_path, engine="openpyxl") as writer:
        # Transactions sheet
        if not cc_df.empty:
            cc_df_export = cc_df.copy()
            # Convert datetime to date for cleaner display
            cc_df_export["TX_Date"] = pd.to_datetime(cc_df_export["TX_Date"]).dt.date
            cc_df_export.to_excel(writer, sheet_name="Transactions", index=False)
            print(f"  ✓ 'Transactions' sheet ({len(cc_df_export)} rows)")
        
        # Metadata sheet
        if metas:
            metas_export = []
            for m in metas:
                metas_export.append({
                    "Period_Start": m["period_start"].date() if m["period_start"] else None,
                    "Period_End": m["period_end"].date() if m["period_end"] else None,
                    "Statement_Date": m["stmt_date"].date() if m["stmt_date"] else None,
                    "Pay_By": m["pay_by"].date() if m["pay_by"] else None,
                    "Total_Amount_Due": m["tad"],
                    "PDF_Path": m["pdf_path"],
                })
            metas_df = pd.DataFrame(metas_export)
            metas_df.to_excel(writer, sheet_name="Metadata", index=False)
            print(f"  ✓ 'Metadata' sheet ({len(metas_df)} statements)")
    
    print(f"\n✓ Cache saved: {cache_path}\n")
    
    # Display summary
    print("=== SUMMARY ===")
    for m in sorted(metas, key=lambda x: x["period_start"]):
        df_rows = cc_df[cc_df["Statement_Period"].str.startswith(
            m["period_start"].strftime("%b-%Y")
        )] if not cc_df.empty else pd.DataFrame()
        spend_total = df_rows["DR"].sum() if not df_rows.empty else 0
        count = len(df_rows)
        print(f"  {m['period_start'].strftime('%d-%b-%Y')} → {m['period_end'].strftime('%d-%b-%Y')} | {count:3d} TXs | Total: ₹{spend_total:10,.2f}")
    
    return cache_path

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Extract CC statement PDFs to Excel cache (one-time operation)"
    )
    parser.add_argument(
        "--fy", default="FY26",
        choices=["FY25", "FY26"],
        help="Fiscal year (default: FY26)"
    )
    parser.add_argument(
        "--cc-dir", default=r"E:\Tax\Aayush\credit_card_statements",
        help="Directory containing Kotak CC statement PDFs"
    )
    
    args = parser.parse_args()
    
    try:
        cache_path = extract_and_cache(args.fy, Path(args.cc_dir))
        print(f"✓ Extraction complete. Use '{cache_path.name}' for faster narration runs.")
    except Exception as e:
        print(f"✗ Error: {e}")
        sys.exit(1)
