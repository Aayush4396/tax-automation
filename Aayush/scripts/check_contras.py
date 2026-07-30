# -*- coding: utf-8 -*-
"""
check_contras.py
================
Verifies whether all identified self-transfers (Contras) in Aayush's bank statements
are matching symmetrically across accounts.

Usage:
    python check_contras.py [--fy FY26] [--file PATH]
"""

import sys
import io
import argparse
import re
from pathlib import Path
import pandas as pd
from openpyxl import load_workbook

# Force UTF-8 output on Windows
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

BANK_MAP = {
    "SBI 1227": "SBI",
    "KOTAK 0333": "KOTAK",
    "FEDERAL 0847": "FEDERAL",
    "AXIS": "AXIS",
    "HDFC 5413": "HDFC",
    "SBM": "SBM Bank",
}

# Reverse mapping for display names
DISPLAY_TO_KEY = {
    "SBI": "SBI",
    "KOTAK": "KOTAK",
    "FEDERAL": "FEDERAL",
    "AXIS": "AXIS",
    "HDFC": "HDFC",
    "SBM": "SBM Bank",
    "JUPITER": "FEDERAL",
}

def find_header_row(ws_raw):
    """Dynamically locate the row index containing the column headers."""
    for idx, row in enumerate(ws_raw.iter_rows(values_only=True)):
        cells_lower = [str(c).strip().lower() for c in row if c is not None]
        if "date" in cells_lower and "particulars" in cells_lower and ("dr" in cells_lower or "withdrawals" in cells_lower):
            return idx
    return 0

def check_file_contras(file_path: Path):
    if not file_path.exists():
        print(f"File not found: {file_path}")
        return
    
    print(f"\n=================================================================")
    print(f"  VERIFYING CONTRAS FOR: {file_path.name}")
    print(f"  Path: {file_path}")
    print(f"=================================================================")

    wb = load_workbook(file_path, read_only=True)
    sheet_names = wb.sheetnames
    wb.close()
    
    # Exclude non-bank output sheets
    bank_sheets = [s for s in sheet_names if s not in ("For Tally", "Conso", "Bank Summary", "Monthly Pivot", "CC Transactions", "Colour Legend")]
    
    print(f"Found bank sheets: {bank_sheets}")
    
    all_txs = []
    
    for sname in bank_sheets:
        # Load raw sheet first to find header
        wb_temp = load_workbook(file_path, read_only=True)
        ws_temp = wb_temp[sname]
        hdr_idx = find_header_row(ws_temp)
        wb_temp.close()
        
        # Read with pandas using detected header
        df = pd.read_excel(file_path, sheet_name=sname, header=hdr_idx)
        df.columns = [str(c).strip() for c in df.columns]
        
        # Standardize columns
        df = df[df["Particulars"].notna() & (df["Particulars"].astype(str).str.strip().str.lower() != "nan")]
        
        # Check columns
        dr_col = "DR" if "DR" in df.columns else ("Withdrawals" if "Withdrawals" in df.columns else None)
        cr_col = "CR" if "CR" in df.columns else ("Deposits" if "Deposits" in df.columns else None)
        
        if not dr_col or not cr_col:
            continue
            
        df["DR"] = pd.to_numeric(df[dr_col], errors="coerce").fillna(0)
        df["CR"] = pd.to_numeric(df[cr_col], errors="coerce").fillna(0)
        
        # Filter rows with transaction amounts
        df = df[(df["DR"] > 0) | (df["CR"] > 0)].copy()
        
        for idx, row in df.iterrows():
            auto_narr = str(row.get("Auto_Narration", ""))
            human_narr = str(row.get("Human_Narration", ""))
            acc_head = str(row.get("Account_Head", ""))
            particulars = str(row.get("Particulars", ""))
            
            is_contra = False
            target_bank = None
            
            # Identify contra by Auto_Narration
            if "contra" in auto_narr.lower():
                is_contra = True
                m = re.search(r"Contra\s*-\s*(\w+)", auto_narr, re.IGNORECASE)
                if m:
                    target_bank = DISPLAY_TO_KEY.get(m.group(1).upper(), m.group(1).upper())
            
            # Identify contra by Human_Narration
            elif "contra" in human_narr.lower():
                is_contra = True
                m = re.search(r"Contra\s*-\s*(\w+)", human_narr, re.IGNORECASE)
                if m:
                    target_bank = DISPLAY_TO_KEY.get(m.group(1).upper(), m.group(1).upper())
            
            # Identify contra by Account_Head
            elif acc_head in BANK_MAP:
                is_contra = True
                target_bank = BANK_MAP[acc_head]
                
            if is_contra:
                tx_date = pd.to_datetime(row["Date"])
                amount = float(row["DR"]) if float(row["DR"]) > 0 else float(row["CR"])
                direction = "DR" if float(row["DR"]) > 0 else "CR"
                
                # Extract 12-digit RRN
                rrn = None
                m = re.search(r"(?:\b|/|-)(\d{12})(?:\b|/|-)", particulars)
                if m:
                    rrn = m.group(1)
                
                all_txs.append({
                    "sheet": sname,
                    "row_idx": idx + hdr_idx + 2,  # approx Excel row number
                    "date": tx_date,
                    "particulars": particulars,
                    "amount": amount,
                    "direction": direction,
                    "auto_narration": auto_narr,
                    "human_narration": human_narr,
                    "account_head": acc_head,
                    "target_bank": target_bank,
                    "rrn": rrn,
                    "matched": False,
                    "matched_with": None
                })

    print(f"Total identified Contra transactions: {len(all_txs)}")

    # Match pairs
    for i, tx in enumerate(all_txs):
        if tx["matched"]:
            continue
            
        # Look for counterpart in other sheets
        best_match = None
        for j, c_tx in enumerate(all_txs):
            if i == j or c_tx["matched"]:
                continue
            if c_tx["sheet"] == tx["sheet"]:
                continue
                
            # Opposite direction
            if c_tx["direction"] == tx["direction"]:
                continue
                
            # Close amount
            if abs(c_tx["amount"] - tx["amount"]) > 0.05:
                continue
                
            # Match by RRN first
            if tx["rrn"] and c_tx["rrn"] and tx["rrn"] == c_tx["rrn"]:
                best_match = j
                break
                
            # Fallback: Date proximity within +/- 2 days
            days_diff = abs((c_tx["date"] - tx["date"]).days)
            if days_diff <= 2:
                best_match = j
                # Keep checking to see if we find an exact RRN match, otherwise we take this one
                
        if best_match is not None:
            tx["matched"] = True
            all_txs[best_match]["matched"] = True
            tx["matched_with"] = all_txs[best_match]
            all_txs[best_match]["matched_with"] = tx

    # Print results report
    matched_pairs = []
    unmatched = []
    
    for tx in all_txs:
        # Avoid duplicate printing of pairs
        if tx["matched"]:
            # Check if this pair is already in matched_pairs
            pair_exists = False
            for p in matched_pairs:
                if p[0] == tx or p[1] == tx:
                    pair_exists = True
                    break
            if not pair_exists and tx["matched_with"]:
                matched_pairs.append((tx, tx["matched_with"]))
        else:
            unmatched.append(tx)

    print(f"\n--- MATCHED CONTRAS ({len(matched_pairs)} pairs) ---")
    if matched_pairs:
        # Sort by date
        matched_pairs = sorted(matched_pairs, key=lambda x: x[0]["date"])
        for idx, (tx1, tx2) in enumerate(matched_pairs):
            dr_tx = tx1 if tx1["direction"] == "DR" else tx2
            cr_tx = tx2 if tx1["direction"] == "DR" else tx1
            
            print(f"Pair {idx+1:2d}: ₹{dr_tx['amount']:10,.2f}")
            print(f"  Outflow : {dr_tx['sheet']:<10} | Row {dr_tx['row_idx']:3d} | Date: {dr_tx['date'].strftime('%Y-%m-%d')} | Auto: {dr_tx['auto_narration']}")
            print(f"  Inflow  : {cr_tx['sheet']:<10} | Row {cr_tx['row_idx']:3d} | Date: {cr_tx['date'].strftime('%Y-%m-%d')} | Auto: {cr_tx['auto_narration']}")
            if dr_tx["rrn"]:
                print(f"  RRN     : {dr_tx['rrn']}")
            print()
    else:
        print("No matched contras found.")

    print(f"\n--- UNMATCHED CONTRAS ({len(unmatched)} transactions) ---")
    if unmatched:
        # Sort by date
        unmatched = sorted(unmatched, key=lambda x: x["date"])
        for idx, tx in enumerate(unmatched):
            dir_str = "Outflow (DR)" if tx["direction"] == "DR" else "Inflow (CR)"
            print(f"Unmatched {idx+1:2d}: {tx['sheet']:<10} | Row {tx['row_idx']:3d} | Date: {tx['date'].strftime('%Y-%m-%d')} | {dir_str} | Amount: ₹{tx['amount']:,.2f}")
            print(f"  Particulars: {tx['particulars'][:100]}")
            print(f"  Auto Narr  : {tx['auto_narration']} | Head: {tx['account_head']}")
            if tx["target_bank"]:
                print(f"  Target Bank: {tx['target_bank']}")
            if tx["rrn"]:
                print(f"  RRN        : {tx['rrn']}")
            print()
    else:
        print("✓ All contras successfully matched! Symmetric cross-bank verification complete.")
        
    return len(unmatched) == 0

def main():
    parser = argparse.ArgumentParser(description="Verify contra matches across bank sheets")
    parser.add_argument("--fy", default=None, choices=["FY25", "FY26"], help="Financial year to check (checks both if omitted)")
    parser.add_argument("--file", default=None, help="Explicit path to output Excel workbook")
    args = parser.parse_args()

    if args.file:
        check_file_contras(Path(args.file))
    else:
        fyears = [args.fy] if args.fy else ["FY25", "FY26"]
        for fy in fyears:
            file_path = Path(r"e:\Tax\Aayush\Generated Data") / fy / f"Aayush_Consolidated_Bank_Ledger_{fy}.xlsx"
            check_file_contras(file_path)

if __name__ == "__main__":
    main()
