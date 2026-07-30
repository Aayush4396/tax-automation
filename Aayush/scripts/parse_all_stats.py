# -*- coding: utf-8 -*-
import sys
import io
import openpyxl
from pathlib import Path

# Force UTF-8 stdout
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

def parse_bank_summary(file_path):
    wb = openpyxl.load_workbook(file_path, data_only=True)
    if 'Bank Summary' not in wb.sheetnames:
        return {"error": "Bank Summary sheet not found"}
    
    ws = wb['Bank Summary']
    
    # Let's extract:
    # 1. Bank balances (Opening & Closing)
    # 2. Category pivots
    
    balances = []
    category_summary = []
    
    # We will scan the worksheet
    rows = []
    for r in range(1, 100):
        row_vals = [ws.cell(r, c).value for c in range(1, 20)]
        rows.append(row_vals)
        
    # Find tables:
    # Look for "Opening Balance" / "Closing Balance"
    # Look for "Account Head" or "Category" or "Narration Pivot"
    
    # Typically, the opening/closing balance table starts with headers like 'Account / Bank', 'Opening Balance', 'Closing Balance'
    # The narration pivot has headers like 'Auto_Narration' or 'Account Head' or similar, followed by Debit, Credit
    
    in_balances_table = False
    in_pivot_table = False
    
    for i, row in enumerate(rows):
        # Clean row
        clean_row = [str(x).strip() if x is not None else "" for x in row]
        # Skip completely empty rows
        if not any(clean_row):
            continue
            
        # Check for balance table headers
        if "Opening Balance" in clean_row or "Opening" in clean_row:
            in_balances_table = True
            in_pivot_table = False
            balance_headers = [x for x in clean_row if x]
            continue
            
        # Check for category pivot table headers
        if "Account Head" in clean_row or "Category" in clean_row or ("Debit" in clean_row and "Credit" in clean_row and "Narration" in clean_row):
            in_balances_table = False
            in_pivot_table = True
            pivot_headers = [x for x in clean_row if x]
            continue
            
        # If we see lines/borders or summary footer, stop or skip
        if any(x.startswith("---") or x.startswith("===") for x in clean_row if x):
            continue
            
        if in_balances_table:
            # If the first cell is empty or looks like total/footer, end table
            if not clean_row[1] or "total" in clean_row[1].lower():
                in_balances_table = False
                if "total" in clean_row[1].lower():
                    balances.append({
                        "bank": "TOTAL",
                        "opening": row[2] or row[3] or 0.0,
                        "closing": row[4] or row[5] or 0.0
                    })
                continue
            
            balances.append({
                "bank": clean_row[1],
                "opening": row[2] or row[3] or 0.0,
                "closing": row[4] or row[5] or 0.0
            })
            
        elif in_pivot_table:
            # If we hit confidence distribution or empty cell, stop
            if not clean_row[1] or "confidence" in clean_row[1].lower() or "total" in clean_row[1].lower():
                # Check if it's the total row of category pivot
                if "total" in clean_row[1].lower():
                    category_summary.append({
                        "category": "TOTAL",
                        "debit": row[2] or 0.0,
                        "credit": row[3] or 0.0
                    })
                in_pivot_table = False
                continue
                
            category_summary.append({
                "category": clean_row[1],
                "debit": row[2] or 0.0,
                "credit": row[3] or 0.0
            })
            
    wb.close()
    return {
        "balances": balances,
        "categories": category_summary
    }

def print_fy_report(year, path):
    print(f"\n==================== {year} STATS ====================")
    if not Path(path).exists():
        print(f"File not found: {path}")
        return
        
    data = parse_bank_summary(path)
    if "error" in data:
        print(data["error"])
        return
        
    print("\n--- BANK BALANCES (Opening -> Closing) ---")
    for b in data["balances"]:
        bank_name = b["bank"]
        op = b["opening"]
        cl = b["closing"]
        # Format if float
        op_str = f"₹{op:,.2f}" if isinstance(op, (int, float)) else str(op)
        cl_str = f"₹{cl:,.2f}" if isinstance(cl, (int, float)) else str(cl)
        diff_str = ""
        if isinstance(op, (int, float)) and isinstance(cl, (int, float)):
            diff = cl - op
            diff_str = f" (Net: {'+' if diff >= 0 else ''}₹{diff:,.2f})"
        print(f"  {bank_name:<25}: {op_str} -> {cl_str}{diff_str}")
        
    print("\n--- TOP CATEGORIES (DEBITS / PAYMENTS) ---")
    debits = [c for c in data["categories"] if c["category"] != "TOTAL" and isinstance(c["debit"], (int, float)) and c["debit"] > 0]
    debits.sort(key=lambda x: x["debit"], reverse=True)
    for d in debits[:10]:
        val = d["debit"]
        print(f"  {d['category']:<25}: ₹{val:,.2f}")
        
    print("\n--- TOP CATEGORIES (CREDITS / RECEIPTS) ---")
    credits = [c for c in data["categories"] if c["category"] != "TOTAL" and isinstance(c["credit"], (int, float)) and c["credit"] > 0]
    credits.sort(key=lambda x: x["credit"], reverse=True)
    for c in credits[:10]:
        val = c["credit"]
        print(f"  {c['category']:<25}: ₹{val:,.2f}")

    # Total credits & debits
    total_row = [c for c in data["categories"] if c["category"] == "TOTAL"]
    if total_row:
        t = total_row[0]
        deb = t["debit"]
        cre = t["credit"]
        deb_str = f"₹{deb:,.2f}" if isinstance(deb, (int, float)) else str(deb)
        cre_str = f"₹{cre:,.2f}" if isinstance(cre, (int, float)) else str(cre)
        print(f"\n  TOTAL TRANSACTIONS VALUE - Debits: {deb_str} | Credits: {cre_str}")

# Run parser
print_fy_report("FY24", r"E:\Tax\Aayush\Bank Statements\FY24\All Banks_Aayush FY23-24.xlsx")
print_fy_report("FY25", r"E:\Tax\Aayush\Generated Data\FY25\Aayush_Consolidated_Bank_Ledger_FY25.xlsx")
print_fy_report("FY26", r"E:\Tax\Aayush\Generated Data\FY26\Aayush_Consolidated_Bank_Ledger_FY26.xlsx")
