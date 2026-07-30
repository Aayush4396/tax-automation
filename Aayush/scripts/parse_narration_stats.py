# -*- coding: utf-8 -*-
import sys
import io
import openpyxl
import pandas as pd
from pathlib import Path

# Force UTF-8 stdout
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

def get_narration_stats(file_path, label):
    if not Path(file_path).exists():
        return None
        
    wb = openpyxl.load_workbook(file_path, data_only=True)
    
    # Identify bank sheets
    ignored_sheets = {'For Tally', 'Conso', 'Bank Summary', 'Monthly Pivot', 'CC Transactions', 'Colour Legend', 'CC_Transactions'}
    bank_sheets = [s for s in wb.sheetnames if s not in ignored_sheets]
    
    # We will read each sheet into a dataframe
    total_tx = 0
    high_conf = 0
    med_conf = 0
    low_conf = 0
    
    matches = 0
    diffs = 0
    nas = 0
    
    sheet_details = []
    
    for sheet in bank_sheets:
        ws = wb[sheet]
        
        # We need to find the header row because it could be at index > 1
        # Let's read first 30 rows to detect header
        rows = list(ws.iter_rows(values_only=True))
        hdr_idx = None
        for i, r in enumerate(rows):
            if any(x == 'Particulars' or x == 'Confidence' for x in r if x is not None):
                hdr_idx = i
                break
        
        if hdr_idx is None:
            # Let's try matching a row with most headers
            for i, r in enumerate(rows):
                non_null_keys = [str(x).strip().lower() for x in r if x is not None]
                if 'date' in non_null_keys and ('debit' in non_null_keys or 'dr' in non_null_keys or 'withdrawal' in non_null_keys):
                    hdr_idx = i
                    break
        
        if hdr_idx is None:
            # Fallback to row 0 if we can't find it
            hdr_idx = 0
            
        # Parse sheet as pandas DataFrame
        df = pd.read_excel(file_path, sheet_name=sheet, header=hdr_idx)
        df.columns = [str(c).strip() for c in df.columns]
        
        # Clean columns: we want 'Confidence' and 'Match'
        # Check if they exist
        if 'Confidence' not in df.columns:
            # Try partial matching or skip
            conf_col = None
            for col in df.columns:
                if 'confid' in col.lower():
                    conf_col = col
                    break
        else:
            conf_col = 'Confidence'
            
        if 'Match' not in df.columns:
            match_col = None
            for col in df.columns:
                if 'match' in col.lower():
                    match_col = col
                    break
        else:
            match_col = 'Match'
            
        # Let's filter out rows where Date or Particulars are empty/null to avoid summary or empty rows
        # Or rows where both DR and CR are 0 / null
        dr_col = next((c for c in df.columns if c.lower() in ('dr', 'debit', 'withdrawal amt.')), None)
        cr_col = next((c for c in df.columns if c.lower() in ('cr', 'credit', 'deposit amt.')), None)
        
        if dr_col and cr_col:
            df = df[(df[dr_col].notna() & (df[dr_col] > 0)) | (df[cr_col].notna() & (df[cr_col] > 0))]
        else:
            # fallback filter out rows that are entirely empty or have no confidence
            if conf_col:
                df = df[df[conf_col].notna()]
                
        if df.empty:
            continue
            
        s_total = len(df)
        s_high = 0
        s_med = 0
        s_low = 0
        s_match = 0
        s_diff = 0
        s_na = 0
        
        if conf_col:
            confs = pd.to_numeric(df[conf_col], errors='coerce').fillna(0)
            s_high = (confs >= 0.85).sum()
            s_med = ((confs >= 0.60) & (confs < 0.85)).sum()
            s_low = (confs < 0.60).sum()
            
        if match_col:
            matches_series = df[match_col].astype(str).str.strip().str.upper()
            s_match = matches_series.str.contains('MATCH').sum()
            s_diff = matches_series.str.contains('DIFF').sum()
            s_na = (matches_series.str.contains('N/A') | matches_series.str.contains('NAN') | (matches_series == '')).sum()
            
        sheet_details.append({
            "sheet": sheet,
            "total": s_total,
            "high": s_high,
            "medium": s_med,
            "low": s_low,
            "match": s_match,
            "diff": s_diff,
            "na": s_na
        })
        
        total_tx += s_total
        high_conf += s_high
        med_conf += s_med
        low_conf += s_low
        matches += s_match
        diffs += s_diff
        nas += s_na
        
    wb.close()
    return {
        "year": label,
        "total": total_tx,
        "high": high_conf,
        "medium": med_conf,
        "low": low_conf,
        "match": matches,
        "diff": diffs,
        "na": nas,
        "sheets": sheet_details
    }

def print_narration_stats(stats):
    if not stats:
        print("No data available.")
        return
        
    print(f"\n==================== {stats['year']} NARRATION STATS ====================")
    print(f"Total Transactions Across Bank Sheets: {stats['total']}")
    
    if stats['total'] > 0:
        high_pct = (stats['high'] / stats['total']) * 100
        med_pct = (stats['medium'] / stats['total']) * 100
        low_pct = (stats['low'] / stats['total']) * 100
        
        print("\n--- Confidence Level Distribution ---")
        print(f"  High (>= 0.85) : {stats['high']:>4} ({high_pct:.1f}%)")
        print(f"  Medium (0.60-0.84): {stats['medium']:>4} ({med_pct:.1f}%)")
        print(f"  Low (< 0.60)   : {stats['low']:>4} ({low_pct:.1f}%)")
        
        print("\n--- Match vs Human Narration ---")
        print(f"  Match [MATCH]  : {stats['match']:>4}")
        print(f"  Mismatch [DIFF]: {stats['diff']:>4}")
        print(f"  No Human Narr  : {stats['na']:>4}")
        
        # Calculate accuracy on reviewed records
        reviewed = stats['match'] + stats['diff']
        if reviewed > 0:
            accuracy = (stats['match'] / reviewed) * 100
            print(f"  Narration Accuracy on Reviewed: {accuracy:.1f}% (Total Reviewed: {reviewed})")
        else:
            print("  Narration Accuracy: N/A (No human narration matched)")
            
        print("\n--- Per-Sheet Breakdown ---")
        print(f"  {'Sheet Name':<25} | {'Total':<5} | {'High':<5} | {'Med':<5} | {'Low':<5} | {'Match':<5} | {'Diff':<5}")
        print(f"  {'-'*25}-|-{'-'*5}-|-{'-'*5}-|-{'-'*5}-|-{'-'*5}-|-{'-'*5}-|-{'-'*5}")
        for s in stats['sheets']:
            print(f"  {s['sheet']:<25} | {s['total']:<5} | {s['high']:<5} | {s['medium']:<5} | {s['low']:<5} | {s['match']:<5} | {s['diff']:<5}")

stats_fy24 = get_narration_stats(r"E:\Tax\Aayush\Generated Data\FY24\Aayush_Consolidated_Bank_Ledger_FY24.xlsx", "FY24")
stats_fy25 = get_narration_stats(r"E:\Tax\Aayush\Generated Data\FY25\Aayush_Consolidated_Bank_Ledger_FY25.xlsx", "FY25")
stats_fy26 = get_narration_stats(r"E:\Tax\Aayush\Generated Data\FY26\Aayush_Consolidated_Bank_Ledger_FY26.xlsx", "FY26")

print_narration_stats(stats_fy24)
print_narration_stats(stats_fy25)
print_narration_stats(stats_fy26)
