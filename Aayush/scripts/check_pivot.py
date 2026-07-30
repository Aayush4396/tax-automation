import warnings; warnings.filterwarnings("ignore")
import pandas as pd, sys
sys.path.insert(0, r"E:\Tax\scripts")
from run_narration import parse_sheet

path = r"E:\Tax\Bank Statements\FY26\Aayush Acct_Statement_XXXXXXXX5413_14042026.xlsx"

# Check all banks for Ajay Gupta inflows around Jan-Feb 2026
print("=== All Ajay Gupta transfers (any direction) ===")
for sheet in ["HDFC", "AXIS", "SBI", "KOTAK"]:
    df, _, _, _ = parse_sheet(path, sheet)
    df["TX_Date"] = pd.to_datetime(df["TX_Date"], errors="coerce")
    ajay = df[df["Particulars"].astype(str).str.contains("AJAY|AKG", case=False)]
    if not ajay.empty:
        print(f"--- {sheet} ---")
        print(ajay[["TX_Date","DR","CR","Auto_Narration","Particulars"]].to_string(index=False))
        print()

# Also check for any ~40k CR after Jan 2026
print("=== Any CR >= 35000 after 2026-01-01 (possible Ajay return) ===")
for sheet in ["HDFC", "AXIS", "SBI", "KOTAK"]:
    df, _, _, _ = parse_sheet(path, sheet)
    df["TX_Date"] = pd.to_datetime(df["TX_Date"], errors="coerce")
    big_cr = df[(df["CR"] >= 35000) & (df["TX_Date"] >= "2026-01-01")]
    if not big_cr.empty:
        print(f"--- {sheet} ---")
        print(big_cr[["TX_Date","DR","CR","Auto_Narration","Particulars"]].to_string(index=False))
        print()
