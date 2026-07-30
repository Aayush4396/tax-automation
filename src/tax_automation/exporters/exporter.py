# -*- coding: utf-8 -*-
"""
exporter.py
===========
Writes all sheets of the output workbook:
  • One colour-coded narrated sheet per bank
  • For Tally sheet (all banks, date-sorted)
  • Conso sheet (all banks, with totals header)
  • Bank Summary sheet (pivot + opening/closing balances + confidence stats)
"""

from __future__ import annotations
import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import PatternFill, Font, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from tax_automation.config_loader import get_exporter_theme_config

_theme_cfg = get_exporter_theme_config()
_THEME_COLOUR_MAP = _theme_cfg.get("colour_map", {})

# ── Palette ────────────────────────────────────────────────────────────────
_BASE_COLOUR_MAP: dict[str, str] = {
    "Broadband & WiFi": "D5F0E8",
    "Groceries & Household": "D5F5CC",
    "Food & Dining": "FFD5CC",
    "Rent": "FDDCB5",
    "Travel & Commute": "CCE8FF",
    "Fuel": "FFF5CC",
    "Transport & Automotive": "CCF0FF",
    "Healthcare & Medical": "F8D7DA",
    "Life Insurance": "F5C6CB",
    "Health Insurance": "FDDCB5",
    "Subscriptions & Services": "E8D5F5",
    "Utilities & Mobile": "FFF2CC",
    "Shopping & Lifestyle": "F5EDD5",
    "Entertainment & Leisure": "F8D7DA",
    "Investments & Wealth": "D0ECF8",
    "Bank & Depository Charges": "F8D7DA",
    "General/Other Spends": "EDE9F6",
    "Self-Transfer (Contra)": "FFE8CC",
    "Credit Card Payment": "F5D5E8",
    "Salary": "B8F0C4",
    "Freelance & Business Income": "D0F5C8",
    "Dividend Income": "C4EBF0",
    "Bank Interest": "C8F5C8",
    "Investment Inflows (MF/Stocks)": "C8DCF5",
    "Refunds & Reversals": "D5F0E8",
}
COLOUR_MAP: dict[str, str] = {**_BASE_COLOUR_MAP, **_THEME_COLOUR_MAP}

def get_pivot_category_for_row(dr: float, cr: float, head: str, narr: str) -> str:
    try:
        dr = float(dr) if dr is not None else 0.0
    except (ValueError, TypeError):
        dr = 0.0
    try:
        cr = float(cr) if cr is not None else 0.0
    except (ValueError, TypeError):
        cr = 0.0
    head = str(head).strip() if head is not None else ""
    narr = str(narr).strip() if narr is not None else ""
    is_dr = dr > 0

    if is_dr:
        # Check CC payment first
        if narr in ("Credit Card Bill Payment (CRED)", "UPI - CRED", "Credit Card Payment", "Credit Card Bill Payment"):
            return "Credit Card Payment"
        
        # Check Contras
        if narr.startswith("Contra -") or head == "Transfer":
            return "Self-Transfer (Contra)"
            
        # Match other payment rules
        if narr == "Airtel WiFi":
            return "Broadband & WiFi"
        if head == "Groceries" or any(k in narr for k in ("UPI - DMart", "UPI - Fresh Produce", "UPI - Nandini Dairy", "UPI - Star Bazaar", "UPI - Zepto")):
            return "Groceries & Household"
        if head == "Food & Dining" or any(k in narr for k in ("Food & Dining", "UPI - District (Dining)", "UPI - Swiggy", "UPI - Zomato")):
            return "Food & Dining"
        if head == "Rent" or any(k in narr for k in ("Rent", "Rent Payment (via CRED)")):
            return "Rent"
        if head == "Travel" or narr == "UPI - IRCTC":
            return "Travel & Commute"
        if head == "Fuel & Petrol" or "Fuel" in narr:
            return "Fuel"
        if head == "Transport" or any(k in narr for k in ("Toll / FASTag", "Vehicle Service")):
            return "Transport & Automotive"
        if head == "Healthcare" or head == "Medical" or any(k in narr for k in ("UPI - MedPlus", "UPI - Pharmacy")):
            return "Healthcare & Medical"
        if head == "Life Insurance" or any(k in narr for k in ("Life Insurance Premium", "Premium Payment (ECS Return Charge)")):
            return "Life Insurance"
        if head == "Health Insurance" or narr == "Health Insurance":
            return "Health Insurance"
        if head == "Subscriptions" or any(k in narr for k in ("UPI - Google Play", "UPI - Hotstar", "UPI - OpenAI")):
            return "Subscriptions & Services"
        if head == "Utilities" or narr == "Govt / Utility Payment":
            return "Utilities & Mobile"
        if head == "Shopping" or any(k in narr for k in ("Shopping - Jewellery", "UPI - Amazon", "UPI - Flipkart")):
            return "Shopping & Lifestyle"
        if head == "Entertainment":
            return "Entertainment & Leisure"
        if head in ("SIP", "PPF Deposit", "HDFC Securities", "Mutual Funds", "IPO", "Investments") or any(k in narr for k in ("SIP", "SBI PPF", "HDFC Securities - Buy", "Securities Settlement", "MF Investment", "INDmoney Investment", "IPO - Billion Garages", "IPO - JSW Cement")):
            return "Investments & Wealth"
        if head in ("Bank Charges", "Depository Charges") or any(k in narr for k in ("Bank Charges", "Lounge Access Charge", "Depository Charges")):
            return "Bank & Depository Charges"
            
        return "General/Other Spends"
    else:
        # Receipts
        if narr.startswith("Contra -") or head == "Transfer":
            return "Self-Transfer (Contra)"
            
        if head == "Salary" or narr == "Salary":
            return "Salary"
        if head == "Freelance Income" or narr == "Freelance Income":
            return "Freelance & Business Income"
        if head == "Dividend Income" or narr == "Dividend Income":
            return "Dividend Income"
        if head == "Bank Interest" or narr == "Bank Interest":
            return "Bank Interest"
        if head in ("Mutual Funds", "CDSL", "HDFC Securities") or any(k in narr for k in ("MF Redemption", "Depository Credit", "HDFC Securities - Sell", "HDFC Securities - Settlement")):
            return "Investment Inflows (MF/Stocks)"
        if any(k in narr for k in ("Refund - Wakefit", "Security Deposit Return", "UPI Reversal", "Income Tax Refund", "Cashback - BHIM", "Cashback - Kiwi", "SuperMoney (Rewards)")):
            return "Refunds & Reversals"
            
        return "Personal Inflows / Transfers"

def get_cc_pivot_category(narr: str) -> str:
    n = str(narr).strip()
    if n == "CC - Wifi": return "Broadband & WiFi"
    if n == "CC - Groceries": return "Groceries & Household"
    if n == "CC - Restaurants": return "Food & Dining"
    if n == "CC - Travel": return "Travel & Commute"
    if n == "CC - Fuel": return "Fuel"
    if n == "CC - Automotive": return "Transport & Automotive"
    if n == "CC - Healthcare": return "Healthcare & Medical"
    if n == "CC - Services": return "Subscriptions & Services"
    if n in ("CC - Telecom", "CC - Utilities"): return "Utilities & Mobile"
    if n == "CC - Shopping": return "Shopping & Lifestyle"
    if n in ("CC - Entertainment", "CC - Recreation"): return "Entertainment & Leisure"
    return "General/Other Spends"

def assign_pivot_categories(all_df: pd.DataFrame) -> pd.DataFrame:
    df = all_df.copy()
    df["Pivot_Category"] = df.apply(
        lambda r: get_pivot_category_for_row(r.get("DR", 0), r.get("CR", 0), r.get("Account_Head", ""), r.get("Auto_Narration", "")),
        axis=1
    )
    return df

_DEFAULT_COLOUR   = "FFFFFF"
_CONF_HIGH_COLOUR = "C6EFCE"   # green  — High confidence (≥0.85)
_CONF_MED_COLOUR  = "FFEB9C"   # amber  — Medium confidence (0.60–0.84)
_CONF_LOW_COLOUR  = "FFC7CE"   # red    — Low confidence  (<0.60)

# ── Shared style helpers ────────────────────────────────────────────────────
_THIN = Side(style="thin", color="D0D0D0")
_BORDER = Border(left=_THIN, right=_THIN, top=_THIN, bottom=_THIN)
_HDR_FILL = PatternFill("solid", fgColor="1A1A2E")
_HDR_FONT = Font(bold=True, color="FFFFFF", size=10)
_HDR_ALIGN = Alignment(horizontal="center", vertical="center", wrap_text=True)
_DIFF_FONT = Font(bold=True, color="8B0000")
_CELL_ALIGN = Alignment(vertical="center", wrap_text=False)


def _write_header(ws, columns: list[str]):
    ws.append(columns)
    for cell in ws[ws.max_row]:
        cell.fill  = _HDR_FILL
        cell.font  = _HDR_FONT
        cell.alignment = _HDR_ALIGN


def _get_row_colour(label: str) -> str:
    """Resolve a row background colour from Auto_Narration / Account_Head label.
    Handles prefix patterns like 'Received - Name' → UPI Receipt colour,
    while preserving specific 'Transfer - Name' colours if defined."""
    if label in COLOUR_MAP:
        return COLOUR_MAP[label]
    if label.startswith("Received - "):
        name = label.replace("Received - ", "")
        transfer_label = f"Transfer - {name}"
        if transfer_label in COLOUR_MAP:
            return COLOUR_MAP[transfer_label]
        return COLOUR_MAP.get("UPI Receipt", _DEFAULT_COLOUR)
    if label.startswith("Paid - "):
        name = label.replace("Paid - ", "")
        transfer_label = f"Transfer - {name}"
        if transfer_label in COLOUR_MAP:
            return COLOUR_MAP[transfer_label]
        return COLOUR_MAP.get("UPI Payment", _DEFAULT_COLOUR)
    return _DEFAULT_COLOUR


def _write_local_legend(ws, unique_narrs: list[str], display_name: str):
    """
    Writes a compact horizontal legend of category colours used in this sheet at the top.
    """
    # Title
    ws.cell(1, 2, f"{display_name} Narration Sheet").font = Font(bold=True, size=12, color="1A1A2E")
    
    ws.cell(2, 2, "Colour Legend of Categories:").font = Font(bold=True, size=10, color="1F3A60")
    
    # Filter out standard blank or default fills
    colored_narrs = []
    # Deduplicate unique narrations by their full narration label
    seen_labels = set()
    for narr in unique_narrs:
        bg_col = _get_row_colour(narr)
        if bg_col != _DEFAULT_COLOUR:
            # Keep the full narration label (e.g. "Received - Megha Gupta", "SIP", etc.)
            # so every distinct category has a legend entry.
            if narr not in seen_labels:
                seen_labels.add(narr)
                colored_narrs.append((narr, bg_col))
            
    if not colored_narrs:
        ws.cell(3, 2, "No specific category colours used in this sheet.").font = Font(italic=True, size=9)
        ws.append([]) # spacer
        return
        
    # Write them in a grid: 5 columns wide starting at Column B (col 2)
    cols_per_row = 5
    curr_row = 3
    curr_col = 2
    
    for label, bg_col in colored_narrs:
        cell = ws.cell(curr_row, curr_col, label)
        cell.fill = PatternFill("solid", fgColor=bg_col)
        cell.font = Font(bold=True, size=9)
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = _BORDER
        
        curr_col += 1
        if curr_col > 2 + cols_per_row - 1:
            curr_col = 2
            curr_row += 1
            
    # Ensure spacer row
    ws.append([])


def _auto_col_widths(ws, df: pd.DataFrame):
    for i, col in enumerate(df.columns, 1):
        try:
            max_len = max(len(str(col)),
                          df[col].astype(str).str.len().max() if len(df) > 0 else 0)
        except Exception:
            max_len = len(str(col))
        ws.column_dimensions[get_column_letter(i)].width = min(max_len + 4, 60)


def _colour_rows(ws, narr_col_idx: int, conf_col_idx: int,
                 match_col_idx: int | None, start_row: int = 2):
    for row in ws.iter_rows(min_row=start_row, max_row=ws.max_row):
        narr_val  = str(row[narr_col_idx - 1].value or "")
        conf_val  = row[conf_col_idx - 1].value if conf_col_idx else None
        row_colour = _get_row_colour(narr_val)
        fill = PatternFill("solid", fgColor=row_colour)
        is_diff = (match_col_idx and row[match_col_idx - 1].value == "[DIFF]")
        for cell in row:
            cell.fill      = fill
            cell.border    = _BORDER
            cell.alignment = _CELL_ALIGN
            if is_diff:
                cell.font = _DIFF_FONT
        # 3-tier confidence colour on the Confidence cell
        if conf_val is not None:
            try:
                conf_f = float(conf_val)
                if conf_f >= 0.85:
                    conf_colour = _CONF_HIGH_COLOUR
                elif conf_f >= 0.60:
                    conf_colour = _CONF_MED_COLOUR
                else:
                    conf_colour = _CONF_LOW_COLOUR
                row[conf_col_idx - 1].fill = PatternFill("solid", fgColor=conf_colour)
            except (ValueError, TypeError):
                pass



# ── Per-bank sheet ──────────────────────────────────────────────────────────

def write_bank_sheet(wb: Workbook, df: pd.DataFrame,
                     sheet_name: str, display_name: str):
    """Write a single colour-coded bank narration sheet."""
    ws = wb.create_sheet(title=sheet_name[:31])

    # Rename TX_Date to Date if it exists
    df_clean = df.copy()
    if "TX_Date" in df_clean.columns and "Date" not in df_clean.columns:
        df_clean = df_clean.rename(columns={"TX_Date": "Date"})

    # Write horizontal colour legend at the top
    unique_narrs = list(df_clean["Auto_Narration"].dropna().unique())
    _write_local_legend(ws, unique_narrs, display_name)

    export_cols = [c for c in [
        "Date", "Particulars", "Ref", "Value_Date",
        "DR", "CR", "Balance",
        "Beneficiary",
        "Human_Narration",
        "Auto_Narration", "Account_Head", "Confidence", "Match", "Duplicate",
    ] if c in df_clean.columns]

    _write_header(ws, export_cols)
    hdr_row = ws.max_row

    for _, row in df_clean[export_cols].iterrows():
        ws.append([row[c] for c in export_cols])

    narr_idx  = export_cols.index("Auto_Narration") + 1
    conf_idx  = export_cols.index("Confidence") + 1 if "Confidence" in export_cols else None
    match_idx = export_cols.index("Match") + 1       if "Match"      in export_cols else None

    _colour_rows(ws, narr_idx, conf_idx, match_idx, start_row=hdr_row + 1)
    _auto_col_widths(ws, df_clean[export_cols])
    
    # Hide requested columns
    cols_to_hide = ["Date", "Value_Date", "Ref", "Balance", "Human_Narration", "Beneficiary"]
    for col_name in cols_to_hide:
        if col_name in export_cols:
            idx = export_cols.index(col_name) + 1
            col_letter = get_column_letter(idx)
            ws.column_dimensions[col_letter].hidden = True
            
    ws.freeze_panes = f"A{hdr_row + 1}"
    ws.auto_filter.ref = f"A{hdr_row}:{get_column_letter(len(export_cols))}{ws.max_row}"


# ── For Tally sheet ─────────────────────────────────────────────────────────

def write_for_tally(wb: Workbook, all_df: pd.DataFrame):
    ws = wb.create_sheet(title="For Tally")

    cols = ["TX_Date", "Value_Date", "DR", "CR",
            "Beneficiary", "Auto_Narration", "Confidence", "Account_Head",
            "Account_ID", "Human_Narration", "Particulars", "Bank_Display", "Duplicate", "Pivot_Category"]

    # Rename to match original header labels
    rename = {
        "TX_Date"      : "TX Date",
        "Value_Date"   : "Date",
        "Auto_Narration": "Narration",
        "Account_Head" : "Account Head",
        "Account_ID"   : "Account No",
        "Human_Narration": "Kya Hai?",
        "Bank_Display" : "Bank",
        "Pivot_Category": "Pivot Category",
    }
    out_cols = [c for c in cols if c in all_df.columns]
    out_df   = all_df[out_cols].copy().rename(columns=rename)

    _write_header(ws, list(out_df.columns))
    hdr_row = ws.max_row

    for _, row in out_df.iterrows():
        ws.append(list(row))

    narr_idx = list(out_df.columns).index("Narration") + 1
    conf_idx = list(out_df.columns).index("Confidence") + 1 if "Confidence" in out_df.columns else None
    _colour_rows(ws, narr_idx, conf_idx, None, start_row=hdr_row + 1)
    _auto_col_widths(ws, out_df)
    
    # Hide requested columns
    tally_cols_to_hide = ["TX Date", "Date", "Beneficiary", "Kya Hai?", "Pivot Category"]
    for col_name in tally_cols_to_hide:
        if col_name in out_df.columns:
            idx = list(out_df.columns).index(col_name) + 1
            col_letter = get_column_letter(idx)
            ws.column_dimensions[col_letter].hidden = True
            
    ws.freeze_panes = f"A{hdr_row + 1}"
    ws.auto_filter.ref = f"A{hdr_row}:{get_column_letter(len(out_df.columns))}{ws.max_row}"


# ── Conso sheet ─────────────────────────────────────────────────────────────

def write_conso(wb: Workbook, all_df: pd.DataFrame, fy_label: str,
                account_holder: str = "Aayush Kumar Gupta"):
    ws = wb.create_sheet(title="Conso")

    max_row = len(all_df) + 4

    # Header block
    ws.append([account_holder])
    ws.append([f"Account of Statements from {fy_label}",
               None, None, f"=SUBTOTAL(9, D5:D{max_row})", f"=SUBTOTAL(9, E5:E{max_row})", "=E2-D2"])
    ws.append([])  # blank separator

    # Column headers
    conso_cols = ["TX_Date", "Particulars", "Ref",
                  "DR", "CR", "Balance", "Account_Head", "Account_ID"]
    out_cols   = [c for c in conso_cols if c in all_df.columns]
    header_row = ["TX Date", "Particulars", "Ref",
                  "DR", "CR", "Balance", "Account Head", "Account No"][:len(out_cols)]

    _write_header(ws, header_row)
    ws[f"A1"].font = Font(bold=True, size=12)
    ws[f"A2"].font = Font(bold=True)

    for _, row in all_df[out_cols].iterrows():
        ws.append(list(row))

    # Basic formatting
    thin_fill = PatternFill("solid", fgColor="F5F5F5")
    for row in ws.iter_rows(min_row=5, max_row=ws.max_row):
        for cell in row:
            cell.border    = _BORDER
            cell.alignment = _CELL_ALIGN

    # Column widths
    widths = [16, 50, 20, 14, 14, 14, 22, 14]
    for i, w in enumerate(widths[:ws.max_column], 1):
        ws.column_dimensions[get_column_letter(i)].width = w

    # Hide requested columns
    conso_cols_to_hide = ["TX Date", "Ref", "Balance"]
    for col_name in conso_cols_to_hide:
        if col_name in header_row:
            idx = header_row.index(col_name) + 1
            col_letter = get_column_letter(idx)
            ws.column_dimensions[col_letter].hidden = True
            
    ws.freeze_panes = "A5"


# ── Bank Summary sheet ───────────────────────────────────────────────────────

def write_bank_summary(wb: Workbook, all_df: pd.DataFrame,
                       bank_balances: dict[str, tuple[float, float]],
                       fy_label: str,
                       account_holder: str = "Aayush Gupta"):
    """
    bank_balances: { account_id: (opening_balance, closing_balance) }
    """
    ws = wb.create_sheet(title="Bank Summary")

    # ── Title block ──────────────────────────────────────────────────────
    ws.append(["All Banks"])
    ws.append([f"{account_holder} Bank Summary"])
    ws.append([fy_label])
    ws.append([])

    ws["A1"].font = Font(bold=True, size=14)
    ws["A2"].font = Font(bold=True, size=12)

    # Reconstruct For Tally columns dynamically to get column letters
    tally_cols_def = ["TX_Date", "Value_Date", "DR", "CR",
                      "Beneficiary", "Auto_Narration", "Confidence", "Account_Head",
                      "Account_ID", "Human_Narration", "Particulars", "Bank_Display", "Duplicate"]
    tally_rename = {
        "TX_Date"      : "TX Date",
        "Value_Date"   : "Date",
        "Auto_Narration": "Narration",
        "Account_Head" : "Account Head",
        "Account_ID"   : "Account No",
        "Human_Narration": "Kya Hai?",
        "Bank_Display" : "Bank",
    }
    tally_cols = [tally_rename.get(c, c) for c in tally_cols_def if c in all_df.columns]
    dr_col_letter = get_column_letter(tally_cols.index("DR") + 1)
    cr_col_letter = get_column_letter(tally_cols.index("CR") + 1)
    narr_col_letter = get_column_letter(tally_cols.index("Narration") + 1)
    acct_col_letter = get_column_letter(tally_cols.index("Account No") + 1) if "Account No" in tally_cols else None
    conf_col_letter = get_column_letter(tally_cols.index("Confidence") + 1) if "Confidence" in tally_cols else None

    # ── Narration pivot ──────────────────────────────────────────────────
    pivot = (
        all_df.groupby("Auto_Narration")[["CR", "DR"]]
        .sum()
        .sort_index()
        .reset_index()
    )

    # Header row for pivot
    pivot_hdr_row = ws.max_row + 1
    ws.append(["Narration", "Total Credit (₹)", "Narration", "Total Debit (₹)"])
    hdr_fill = PatternFill("solid", fgColor="2C3E50")
    hdr_font = Font(bold=True, color="FFFFFF")
    for cell in ws[pivot_hdr_row]:
        cell.fill = hdr_fill; cell.font = hdr_font
        cell.alignment = _HDR_ALIGN

    pivot_start_row = pivot_hdr_row + 1
    for _, r in pivot.iterrows():
        label = r["Auto_Narration"]

        new_row = ws.max_row + 1
        ws.cell(new_row, 1, label)
        ws.cell(new_row, 2, f"=SUMIFS('For Tally'!{cr_col_letter}:{cr_col_letter}, 'For Tally'!{narr_col_letter}:{narr_col_letter}, A{new_row})")
        ws.cell(new_row, 3, label)
        ws.cell(new_row, 4, f"=SUMIFS('For Tally'!{dr_col_letter}:{dr_col_letter}, 'For Tally'!{narr_col_letter}:{narr_col_letter}, C{new_row})")

        row_colour = _get_row_colour(label)
        fill = PatternFill("solid", fgColor=row_colour)
        for col in range(1, 5):
            cell = ws.cell(new_row, col)
            cell.fill   = fill
            cell.border = _BORDER
            cell.alignment = _CELL_ALIGN

    # Grand total row
    total_row = ws.max_row + 1
    ws.cell(total_row, 1, "TOTAL")
    ws.cell(total_row, 2, f"=SUM(B{pivot_start_row}:B{total_row - 1})")
    ws.cell(total_row, 3, "TOTAL")
    ws.cell(total_row, 4, f"=SUM(D{pivot_start_row}:D{total_row - 1})")
    ws.cell(total_row, 5, "Net")
    ws.cell(total_row, 6, f"=B{total_row}-D{total_row}")
    total_fill = PatternFill("solid", fgColor="2C3E50")
    total_font = Font(bold=True, color="FFFFFF")
    for col in range(1, 7):
        cell = ws.cell(total_row, col)
        cell.fill = total_fill; cell.font = total_font
        cell.alignment = _CELL_ALIGN

    ws.append([])

    # ── Opening / Closing Balances ────────────────────────────────────────
    ws.append(["Opening & Closing Balances"])
    ws[ws.max_row][0].font = Font(bold=True, size=11)

    bal_hdr_row = ws.max_row + 1
    ws.append(["Account", "Opening Balance (₹)", "Closing Balance (₹)"])
    for cell in ws[bal_hdr_row]:
        cell.fill = PatternFill("solid", fgColor="34495E")
        cell.font = Font(bold=True, color="FFFFFF")
        cell.alignment = _HDR_ALIGN

    for acct_id, (opening, closing) in sorted(bank_balances.items()):
        row = ws.max_row + 1
        ws.cell(row, 1, acct_id)
        ws.cell(row, 2, round(opening, 2))
        if acct_col_letter:
            ws.cell(row, 3, f"=B{row} + SUMIFS('For Tally'!{cr_col_letter}:{cr_col_letter}, 'For Tally'!{acct_col_letter}:{acct_col_letter}, A{row}) - SUMIFS('For Tally'!{dr_col_letter}:{dr_col_letter}, 'For Tally'!{acct_col_letter}:{acct_col_letter}, A{row})")
        else:
            ws.cell(row, 3, round(closing, 2))
        for col in range(1, 4):
            ws.cell(row, col).border = _BORDER
            ws.cell(row, col).alignment = _CELL_ALIGN

    ws.append([])

    # ── Confidence Distribution ───────────────────────────────────────────
    ws.append(["Confidence Distribution"])
    ws[ws.max_row][0].font = Font(bold=True, size=11)
    ws.append(["Band", "Count", "% of Total"])

    for cell in ws[ws.max_row]:
        cell.fill = PatternFill("solid", fgColor="34495E")
        cell.font = Font(bold=True, color="FFFFFF")

    bands = [
        ("High (≥ 0.85) — Confident",  ">=0.85", "B8F0C4"),
        ("Medium (0.60–0.84) — Review", "med",  "FFF3CD"),
        ("Low (< 0.60) — Needs attention", "<0.60", "F8D7DA"),
    ]
    conf_start_row = ws.max_row + 1
    for band_label, criteria, colour in bands:
        row = ws.max_row + 1
        ws.cell(row, 1, band_label)
        if conf_col_letter:
            if criteria == ">=0.85":
                ws.cell(row, 2, f"=COUNTIF('For Tally'!{conf_col_letter}:{conf_col_letter}, \">=0.85\")")
            elif criteria == "<0.60":
                ws.cell(row, 2, f"=COUNTIF('For Tally'!{conf_col_letter}:{conf_col_letter}, \"<0.60\")")
            else:
                ws.cell(row, 2, f"=COUNTIFS('For Tally'!{conf_col_letter}:{conf_col_letter}, \">=0.60\", 'For Tally'!{conf_col_letter}:{conf_col_letter}, \"<0.85\")")
        else:
            ws.cell(row, 2, 0)
        ws.cell(row, 3, f"=B{row}/SUM(B{conf_start_row}:B{conf_start_row+2})")
        fill = PatternFill("solid", fgColor=colour)
        for col in range(1, 4):
            cell = ws.cell(row, col)
            cell.fill   = fill
            cell.border = _BORDER
            cell.alignment = _CELL_ALIGN
        ws.cell(row, 3).number_format = "0.0%"

    # Column widths
    ws.column_dimensions["A"].width = 40
    ws.column_dimensions["B"].width = 20
    ws.column_dimensions["C"].width = 20
    ws.column_dimensions["D"].width = 20


# ── CC Transactions sheet ──────────────────────────────────────────────────────

def write_cc_sheet(wb: Workbook, cc_df: pd.DataFrame) -> None:
    """
    Writes a 'CC Transactions' sheet with all itemised Kotak CC spends.
    Columns: Date | Merchant | CC Category | Auto_Narration | DR | CR | Statement Period
    Rows colour-coded by Auto_Narration (same palette as bank sheets).
    Monthly subtotals appended at the end.
    """
    import calendar
    ws = wb.create_sheet(title="CC Transactions")

    if cc_df is None or cc_df.empty:
        ws["A1"] = "No CC transactions loaded."
        return

    df = cc_df.copy()
    df["TX_Date"] = pd.to_datetime(df["TX_Date"], errors="coerce")
    df = df.sort_values("TX_Date").reset_index(drop=True)

    # ── Header ────────────────────────────────────────────────────────────────────
    columns = ["Date", "Merchant", "CC Category", "Auto Narration", "DR (Rs.)", "CR (Rs.)", "Statement Period", "Pivot Category"]
    ws.append(columns)
    hdr_row = ws.max_row
    for cell in ws[hdr_row]:
        cell.fill  = PatternFill("solid", fgColor="1A1A2E")
        cell.font  = Font(bold=True, color="FFFFFF", size=10)
        cell.alignment = _HDR_ALIGN
        cell.border = _BORDER

    # ── Rows ────────────────────────────────────────────────────────────────────────
    prev_month = None
    for _, row in df.iterrows():
        tx_date = row["TX_Date"]
        curr_month = (tx_date.year, tx_date.month) if pd.notna(tx_date) else None

        # Insert a light month-separator row
        if curr_month and curr_month != prev_month:
            if prev_month is not None:
                ws.append([])
            lbl = f"── {calendar.month_abbr[curr_month[1]]}-{curr_month[0]} ──"
            ws.append([lbl])
            sep = ws.max_row
            ws.cell(sep, 1).font  = Font(bold=True, color="555555", italic=True)
            ws.cell(sep, 1).fill  = PatternFill("solid", fgColor="F0F0F0")
            for col in range(1, len(columns) + 1):
                ws.cell(sep, col).fill = PatternFill("solid", fgColor="F0F0F0")
            prev_month = curr_month

        tx_date_val = tx_date.to_pydatetime() if pd.notna(tx_date) else None
        ws.append([
            tx_date_val,
            row.get("Merchant", ""),
            row.get("CC_Category", ""),
            row.get("Auto_Narration", ""),
            round(row["DR"], 2) if row["DR"] > 0 else None,
            round(row["CR"], 2) if row["CR"] > 0 else None,
            row.get("Statement_Period", ""),
            get_cc_pivot_category(row.get("Auto_Narration", "")),
        ])
        fill_colour = COLOUR_MAP.get(row.get("Auto_Narration", ""), _DEFAULT_COLOUR)
        fill = PatternFill("solid", fgColor=fill_colour)
        for col in range(1, len(columns) + 1):
            cell = ws.cell(ws.max_row, col)
            cell.fill = fill
            cell.border = _BORDER
            cell.alignment = _CELL_ALIGN
            if col == 1 and tx_date_val is not None:
                cell.number_format = 'dd-mmm-yyyy'

    tx_end_row = ws.max_row

    # ── Category summary at bottom ─────────────────────────────────────────────
    ws.append([])
    ws.append(["--- CATEGORY TOTALS ---"])
    ws.cell(ws.max_row, 1).font = Font(bold=True)

    summary_start_row = ws.max_row + 1
    cat_totals = df[df["DR"] > 0].groupby("Auto_Narration")["DR"].sum().sort_values(ascending=False)
    for cat, _ in cat_totals.items():
        new_row = ws.max_row + 1
        ws.cell(new_row, 2, cat)
        ws.cell(new_row, 2).font = Font(bold=True)
        ws.cell(new_row, 5, f"=SUMIF(D$2:D${tx_end_row}, B{new_row}, E$2:E${tx_end_row})")
        fill_colour = COLOUR_MAP.get(cat, _DEFAULT_COLOUR)
        for col in [2, 5]:
            ws.cell(new_row, col).fill = PatternFill("solid", fgColor=fill_colour)
            ws.cell(new_row, col).border = _BORDER

    summary_end_row = ws.max_row
    new_row = ws.max_row + 1
    ws.cell(new_row, 2, "GRAND TOTAL")
    if summary_start_row <= summary_end_row:
        ws.cell(new_row, 5, f"=SUM(E{summary_start_row}:E{summary_end_row})")
    else:
        ws.cell(new_row, 5, 0)
        
    for col in [2, 5]:
        ws.cell(new_row, col).font = Font(bold=True)
        ws.cell(new_row, col).fill = PatternFill("solid", fgColor="1A5276")
        ws.cell(new_row, col).font = Font(bold=True, color="FFFFFF")
        ws.cell(new_row, col).border = _BORDER

    # Column widths
    ws.column_dimensions["A"].width = 14
    ws.column_dimensions["B"].width = 28
    ws.column_dimensions["C"].width = 18
    ws.column_dimensions["D"].width = 22
    ws.column_dimensions["E"].width = 12
    ws.column_dimensions["F"].width = 12
    ws.column_dimensions["G"].width = 30
    ws.freeze_panes = "A2"


# ── Monthly Pivot sheet ──────────────────────────────────────────────────────

def write_monthly_pivot(wb: Workbook, all_df: pd.DataFrame,
                        cc_df: pd.DataFrame | None = None) -> None:
    """
    Generates a 'Monthly Pivot' sheet combining both Bank and Credit Card spends
    into unified categories, grouped by Value Date (bank) and Transaction Date (CC).
    """
    import calendar
    ws = wb.create_sheet(title="Monthly Pivot")

    # ── Prepare bank data ────────────────────────────────────────────────────
    df = all_df.copy()
    df["Value_Date"] = pd.to_datetime(df["Value_Date"], errors="coerce")
    df = df.dropna(subset=["Value_Date"])
    df["Month"] = df["Value_Date"].dt.to_period("M")

    # Get CC months
    cc_months = []
    if cc_df is not None and not cc_df.empty:
        cc = cc_df.copy()
        cc["TX_Date"] = pd.to_datetime(cc["TX_Date"], errors="coerce")
        cc = cc.dropna(subset=["TX_Date"])
        cc["Month"] = cc["TX_Date"].dt.to_period("M")
        cc_months = list(cc["Month"].unique())

    # Consolidated list of unique sorted months
    months = sorted(set(df["Month"].unique()) | set(cc_months))
    month_labels = [f"{calendar.month_abbr[m.month]}-{m.year}" for m in months]

    # Reconstruct For Tally columns dynamically to get column letters
    tally_cols_def = ["TX_Date", "Value_Date", "DR", "CR",
                      "Beneficiary", "Auto_Narration", "Confidence", "Account_Head",
                      "Account_ID", "Human_Narration", "Particulars", "Bank_Display", "Duplicate", "Pivot_Category"]
    tally_rename = {
        "TX_Date"      : "TX Date",
        "Value_Date"   : "Date",
        "Auto_Narration": "Narration",
        "Account_Head" : "Account Head",
        "Account_ID"   : "Account No",
        "Human_Narration": "Kya Hai?",
        "Bank_Display" : "Bank",
        "Pivot_Category": "Pivot Category",
    }
    tally_cols = [tally_rename.get(c, c) for c in tally_cols_def if c in all_df.columns]
    
    tally_dr_letter = get_column_letter(tally_cols.index("DR") + 1)
    tally_cr_letter = get_column_letter(tally_cols.index("CR") + 1)
    tally_val_date_letter = get_column_letter(tally_cols.index("Date") + 1)
    tally_bank_letter = get_column_letter(tally_cols.index("Bank") + 1)
    tally_pivot_cat_letter = get_column_letter(tally_cols.index("Pivot Category") + 1)

    unique_banks = sorted(all_df["Bank_Display"].dropna().unique())
    tally_bank_end_letter = get_column_letter(2 + len(unique_banks) - 1)

    # Title
    ws["A1"] = "Unified Monthly Spend & Income Pivot"
    ws["A1"].font = Font(bold=True, size=14)
    ws.append([]) # Row 2 (blank)

    from openpyxl.worksheet.datavalidation import DataValidation

    thin_border = Border(
        left=Side(style='thin', color='A0A0A0'),
        right=Side(style='thin', color='A0A0A0'),
        top=Side(style='thin', color='A0A0A0'),
        bottom=Side(style='thin', color='A0A0A0')
    )
    
    # Bank filter toggles in Row 3
    ws["A3"] = "Bank Filter Toggles:"
    ws["A3"].font = Font(bold=True)
    ws["A3"].alignment = Alignment(horizontal="right")
    
    for idx, bank_name in enumerate(unique_banks):
        cell = ws.cell(3, 2 + idx, bank_name)
        cell.font = Font(bold=True)
        cell.alignment = Alignment(horizontal="center")
        cell.border = thin_border
        cell.fill = PatternFill("solid", fgColor="F2F3F4")

    # Bank toggles in Row 4 (defaulting to True)
    dv_bool = DataValidation(type="list", formula1='"TRUE,FALSE"', allow_blank=False)
    ws.add_data_validation(dv_bool)
    
    for idx in range(len(unique_banks)):
        cell = ws.cell(4, 2 + idx, True)
        cell.font = Font(bold=True, color="1B4F72")
        cell.alignment = Alignment(horizontal="center")
        cell.border = thin_border
        cell.fill = PatternFill("solid", fgColor="EBF5FB")
        dv_bool.add(cell)

    # Helper row in Row 5 (hidden)
    for idx in range(len(unique_banks)):
        col_letter = get_column_letter(2 + idx)
        ws.cell(5, 2 + idx, f'=IF({col_letter}4, {col_letter}3, "")')
    
    ws.row_dimensions[5].hidden = True
    ws.append([]) # Row 6 (blank)

    # ── Payments/Expenses Unified List ───────────────────────────────────────
    PAYMENT_CATEGORIES = [
        "Broadband & WiFi",
        "Groceries & Household",
        "Food & Dining",
        "Rent",
        "Travel & Commute",
        "Fuel",
        "Transport & Automotive",
        "Healthcare & Medical",
        "Life Insurance",
        "Health Insurance",
        "Subscriptions & Services",
        "Utilities & Mobile",
        "Shopping & Lifestyle",
        "Entertainment & Leisure",
        "Investments & Wealth",
        "Bank & Depository Charges",
        "General/Other Spends",
    ]

    # ── DEBIT section (Bank + CC Spends) ─────────────────────────────────────
    ws.append(["PAYMENTS / EXPENSES (Bank + CC)"] + month_labels + ["TOTAL"])
    hdr_row = ws.max_row
    for cell in ws[hdr_row]:
        cell.fill = PatternFill("solid", fgColor="C0392B")
        cell.font = Font(bold=True, color="FFFFFF")
        cell.alignment = _HDR_ALIGN
        cell.border = _BORDER

    debit_start_row = ws.max_row + 1
    for cat in PAYMENT_CATEGORIES:
        new_row = ws.max_row + 1
        ws.cell(new_row, 1, cat)
        
        for i, m in enumerate(months):
            start_date_str = m.start_time.strftime("%Y-%m-%d")
            end_date_str = m.end_time.strftime("%Y-%m-%d")
            
            # Bank part
            formula = (
                f"SUMPRODUCT(SUMIFS('For Tally'!{tally_dr_letter}:{tally_dr_letter}, "
                f"'For Tally'!{tally_pivot_cat_letter}:{tally_pivot_cat_letter}, $A{new_row}, "
                f"'For Tally'!{tally_val_date_letter}:{tally_val_date_letter}, \">={start_date_str}\", "
                f"'For Tally'!{tally_val_date_letter}:{tally_val_date_letter}, \"<={end_date_str}\", "
                f"'For Tally'!{tally_bank_letter}:{tally_bank_letter}, $B$5:${tally_bank_end_letter}$5))"
            )
            # CC part
            if cc_df is not None and not cc_df.empty:
                formula += (
                    f" + SUMIFS('CC Transactions'!E:E, 'CC Transactions'!H:H, $A{new_row}, "
                    f"'CC Transactions'!A:A, \">={start_date_str}\", 'CC Transactions'!A:A, \"<={end_date_str}\")"
                )
            ws.cell(new_row, 2 + i, f"={formula}")

        last_month_col = get_column_letter(2 + len(months) - 1)
        ws.cell(new_row, 2 + len(months), f"=SUM(B{new_row}:{last_month_col}{new_row})")
        
        row_colour = COLOUR_MAP.get(cat, _DEFAULT_COLOUR)
        fill = PatternFill("solid", fgColor=row_colour)
        for cell in ws[ws.max_row]:
            cell.fill = fill; cell.border = _BORDER; cell.alignment = _CELL_ALIGN

    debit_end_row = ws.max_row
    
    # Monthly Debit totals row
    new_row = ws.max_row + 1
    ws.cell(new_row, 1, "EXPENSE TOTAL")
    for i, m in enumerate(months):
        col_letter = get_column_letter(2 + i)
        if debit_start_row <= debit_end_row:
            ws.cell(new_row, 2 + i, f"=SUM({col_letter}{debit_start_row}:{col_letter}{debit_end_row})")
        else:
            ws.cell(new_row, 2 + i, 0)
            
    total_col_letter = get_column_letter(2 + len(months))
    if debit_start_row <= debit_end_row:
        ws.cell(new_row, 2 + len(months), f"=SUM({total_col_letter}{debit_start_row}:{total_col_letter}{debit_end_row})")
    else:
        ws.cell(new_row, 2 + len(months), 0)
        
    for cell in ws[ws.max_row]:
        cell.fill = PatternFill("solid", fgColor="922B21")
        cell.font = Font(bold=True, color="FFFFFF")
        cell.border = _BORDER

    ws.append([]) # spacer

    # ── Receipts/Income Unified List ─────────────────────────────────────────
    RECEIPT_CATEGORIES = [
        "Salary",
        "Freelance & Business Income",
        "Dividend Income",
        "Bank Interest",
        "Investment Inflows (MF/Stocks)",
        "Refunds & Reversals",
        "Personal Inflows / Transfers",
    ]

    # ── CREDIT section (Bank Receipts) ───────────────────────────────────────
    ws.append(["RECEIPTS / INCOME (Bank)"] + month_labels + ["TOTAL"])
    hdr_row2 = ws.max_row
    for cell in ws[hdr_row2]:
        cell.fill = PatternFill("solid", fgColor="1A5276")
        cell.font = Font(bold=True, color="FFFFFF")
        cell.alignment = _HDR_ALIGN
        cell.border = _BORDER

    credit_start_row = ws.max_row + 1
    for cat in RECEIPT_CATEGORIES:
        new_row = ws.max_row + 1
        ws.cell(new_row, 1, cat)
        
        for i, m in enumerate(months):
            start_date_str = m.start_time.strftime("%Y-%m-%d")
            end_date_str = m.end_time.strftime("%Y-%m-%d")
            
            formula = (
                f"SUMPRODUCT(SUMIFS('For Tally'!{tally_cr_letter}:{tally_cr_letter}, "
                f"'For Tally'!{tally_pivot_cat_letter}:{tally_pivot_cat_letter}, $A{new_row}, "
                f"'For Tally'!{tally_val_date_letter}:{tally_val_date_letter}, \">={start_date_str}\", "
                f"'For Tally'!{tally_val_date_letter}:{tally_val_date_letter}, \"<={end_date_str}\", "
                f"'For Tally'!{tally_bank_letter}:{tally_bank_letter}, $B$5:${tally_bank_end_letter}$5))"
            )
            ws.cell(new_row, 2 + i, f"={formula}")
            
        last_month_col = get_column_letter(2 + len(months) - 1)
        ws.cell(new_row, 2 + len(months), f"=SUM(B{new_row}:{last_month_col}{new_row})")
        
        row_colour = COLOUR_MAP.get(cat, _DEFAULT_COLOUR)
        fill = PatternFill("solid", fgColor=row_colour)
        for cell in ws[ws.max_row]:
            cell.fill = fill; cell.border = _BORDER; cell.alignment = _CELL_ALIGN

    credit_end_row = ws.max_row
    
    # Monthly Credit totals row
    new_row = ws.max_row + 1
    ws.cell(new_row, 1, "INFLOW TOTAL")
    for i, m in enumerate(months):
        col_letter = get_column_letter(2 + i)
        if credit_start_row <= credit_end_row:
            ws.cell(new_row, 2 + i, f"=SUM({col_letter}{credit_start_row}:{col_letter}{credit_end_row})")
        else:
            ws.cell(new_row, 2 + i, 0)
            
    if credit_start_row <= credit_end_row:
        ws.cell(new_row, 2 + len(months), f"=SUM({total_col_letter}{credit_start_row}:{total_col_letter}{credit_end_row})")
    else:
        ws.cell(new_row, 2 + len(months), 0)
        
    for cell in ws[ws.max_row]:
        cell.fill = PatternFill("solid", fgColor="1F618D")
        cell.font = Font(bold=True, color="FFFFFF")
        cell.border = _BORDER

    ws.append([]) # spacer

    # ── Self-Transfers section ───────────────────────────────────────────────
    ws.append(["SELF-TRANSFERS (Contra)"] + month_labels + ["TOTAL"])
    hdr_row3 = ws.max_row
    for cell in ws[hdr_row3]:
        cell.fill = PatternFill("solid", fgColor="7F8C8D")
        cell.font = Font(bold=True, color="FFFFFF")
        cell.alignment = _HDR_ALIGN
        cell.border = _BORDER

    contra_start_row = ws.max_row + 1
    new_row = ws.max_row + 1
    ws.cell(new_row, 1, "Self-Transfer (Contra)")
    for i, m in enumerate(months):
        start_date_str = m.start_time.strftime("%Y-%m-%d")
        end_date_str = m.end_time.strftime("%Y-%m-%d")
        
        formula = (
            f"SUMPRODUCT(SUMIFS('For Tally'!{tally_dr_letter}:{tally_dr_letter}, "
            f"'For Tally'!{tally_pivot_cat_letter}:{tally_pivot_cat_letter}, $A{new_row}, "
            f"'For Tally'!{tally_val_date_letter}:{tally_val_date_letter}, \">={start_date_str}\", "
            f"'For Tally'!{tally_val_date_letter}:{tally_val_date_letter}, \"<={end_date_str}\", "
            f"'For Tally'!{tally_bank_letter}:{tally_bank_letter}, $B$5:${tally_bank_end_letter}$5))"
        )
        ws.cell(new_row, 2 + i, f"={formula}")
        
    last_month_col = get_column_letter(2 + len(months) - 1)
    ws.cell(new_row, 2 + len(months), f"=SUM(B{new_row}:{last_month_col}{new_row})")
    
    row_colour = COLOUR_MAP.get("Self-Transfer (Contra)", _DEFAULT_COLOUR)
    fill = PatternFill("solid", fgColor=row_colour)
    for cell in ws[ws.max_row]:
        cell.fill = fill; cell.border = _BORDER; cell.alignment = _CELL_ALIGN

    contra_end_row = ws.max_row
    
    # Monthly Contra totals row
    new_row = ws.max_row + 1
    ws.cell(new_row, 1, "CONTRA TOTAL")
    for i, m in enumerate(months):
        col_letter = get_column_letter(2 + i)
        ws.cell(new_row, 2 + i, f"=SUM({col_letter}{contra_start_row}:{col_letter}{contra_end_row})")
        
    ws.cell(new_row, 2 + len(months), f"=SUM({total_col_letter}{contra_start_row}:{total_col_letter}{contra_end_row})")
    for cell in ws[ws.max_row]:
        cell.fill = PatternFill("solid", fgColor="616A6B")
        cell.font = Font(bold=True, color="FFFFFF")
        cell.border = _BORDER

    # Column widths
    ws.column_dimensions["A"].width = 32
    for i in range(2, len(months) + 3):
        ws.column_dimensions[get_column_letter(i)].width = 14
    ws.freeze_panes = "B8"


def write_colour_legend(wb: Workbook):
    """
    Creates a 'Colour Legend' sheet listing category labels,
    sample background colours, and descriptions.
    """
    ws = wb.create_sheet(title="Colour Legend")
    ws.views.sheetView[0].showGridLines = True
    
    # Title
    ws["B2"] = "Workbook Colour Legend"
    ws["B2"].font = Font(bold=True, size=14, color="1A1A2E")
    
    # Headers
    ws.append([]) # spacer
    ws.append([]) # spacer
    
    ws.append([None, "Category", "Colour Code", "Description"])
    hdr_row = ws.max_row
    for col_idx in [2, 3, 4]:
        cell = ws.cell(hdr_row, col_idx)
        cell.fill = PatternFill("solid", fgColor="1A1A2E")
        cell.font = Font(bold=True, color="FFFFFF", size=10)
        cell.alignment = Alignment(horizontal="center" if col_idx == 3 else "left", vertical="center")
        cell.border = _BORDER

    groups = [
        ("Income & Inflows", [
            ("Salary", "Salary Credit (Mphasis)"),
            ("Bank Interest", "Interest earned on Savings accounts"),
            ("Dividend Income", "Dividend payout from shares"),
            ("Annuity Income", "Annuity credits (HDFC Life)"),
            ("Income Tax Refund", "Income Tax Refund from Department"),
            ("MF Redemption", "Inflows from selling Mutual Funds"),
            ("Upwork Income", "Inward remittances from Upwork freelancing"),
            ("Cash Deposit", "Cash deposits made at CDM / Branch"),
            ("Freelance Income", "Freelance work escrow payouts"),
            ("Cashback - BHIM", "Cashback rewards earned on BHIM app"),
            ("Cashback - Kiwi", "Cashback rewards earned on Kiwi app"),
            ("Refund - Wakefit", "Refund from Wakefit for online shopping"),
        ]),
        ("Investments", [
            ("SIP", "Monthly Mutual Fund SIP payments"),
            ("MF Investment", "Lumpsum Mutual Fund investments"),
            ("Auto Sweep FD", "Sweep in/out between Savings and FD"),
            ("Depository Credit", "CDSL credits / payouts"),
            ("Zerodha Broking", "Payments/payouts associated with Zerodha"),
            ("HDFC Securities - Settlement", "Settlement transfers to HDFC Securities"),
        ]),
        ("Regular Outflows & Insurance", [
            ("Rent", "Rent payments to landlord"),
            ("Life Insurance Premium", "Life insurance premium payments (HDFC Life)"),
            ("Health Insurance", "Health insurance premium payments"),
            ("Security Deposit", "Security deposit paid for rental home"),
            ("Security Deposit Return", "Refund/return of security deposit"),
        ]),
        ("Taxes & Bank Charges", [
            ("Advance Tax", "Advance tax payments"),
            ("Income Tax Payment", "Income tax payments to CBDT"),
            ("Bank Charges", "SMS charges, minimum balance fees, alert fees"),
            ("Depository Charges", "CDSL / DP charges"),
        ]),
        ("Family Transfers", [
            ("Transfer - Sunita Gupta", "Transfers to/from Sunita Gupta"),
            ("Transfer - Ajay Gupta", "Transfers to/from Ajay Gupta"),
            ("Transfer - Archit Gupta", "Transfers to/from Archit Gupta"),
            ("Transfer - Megha Gupta", "Transfers to/from Megha Gupta"),
        ]),
        ("Self Transfers (Contra)", [
            ("Contra - SBI", "Self-transfer to/from State Bank of India"),
            ("Contra - Kotak", "Self-transfer to/from Kotak Mahindra Bank"),
            ("Contra - Jupiter", "Self-transfer to/from Jupiter account"),
            ("Contra - HDFC", "Self-transfer to/from HDFC Bank"),
            ("Contra - Axis", "Self-transfer to/from Axis Bank"),
            ("Contra - SBM", "Self-transfer to/from SBM Bank"),
            ("Contra - Self", "Self-transfer between own accounts"),
            ("Contra - Self (SuperMoney)", "Self-transfer via SuperMoney VPA"),
        ]),
        ("UPI Spend Categories", [
            ("UPI - Zomato", "Food ordering via Zomato"),
            ("UPI - Swiggy", "Food / Instamart ordering via Swiggy"),
            ("UPI - BigBasket", "Grocery shopping via BigBasket / Zepto / Blinkit"),
            ("UPI - Amazon", "Online shopping via Amazon / Flipkart / Ajio"),
            ("UPI - Ola", "Cab / auto booking via Ola / Uber / BluSmart"),
            ("UPI - Netflix", "Subscriptions like Netflix, Spotify, Prime Video"),
            ("UPI - CRED", "Payments made through CRED, PhonePe, Paytm"),
            ("UPI - Apollo", "Medical expenses via Apollo / MedPlus / Wellness"),
            ("UPI - IRCTC", "Train / flight bookings via IRCTC or IndiGo"),
            ("UPI - Fuel", "Fuel purchases at HPCL / BPCL / IOCL pumps"),
        ]),
        ("Generic Fallbacks & Suspense", [
            ("UPI Payment", "Generic outbound UPI transfers to individuals"),
            ("UPI Receipt", "Generic inbound UPI transfers from individuals"),
            ("What is this?", "Suspense items requiring review (Suspense)"),
        ])
    ]

    for grp_title, items in groups:
        # Group Sub-Header
        ws.append([]) # blank separator
        sh_row = ws.max_row
        ws.cell(sh_row, 2, grp_title.upper())
        ws.cell(sh_row, 2).font = Font(bold=True, size=11, color="1F3A60")
        
        for label, desc in items:
            ws.append([None, label, "Sample Fill", desc])
            curr_row = ws.max_row
            
            # Formatting
            ws.cell(curr_row, 2).font = Font(bold=True)
            ws.cell(curr_row, 2).border = _BORDER
            ws.cell(curr_row, 2).alignment = Alignment(horizontal="left", vertical="center")
            
            # Sample Fill cell
            sf_cell = ws.cell(curr_row, 3)
            bg_colour = COLOUR_MAP.get(label, _DEFAULT_COLOUR)
            sf_cell.fill = PatternFill("solid", fgColor=bg_colour)
            sf_cell.font = Font(color="000000" if bg_colour != _DEFAULT_COLOUR else "888888", size=9)
            sf_cell.alignment = Alignment(horizontal="center", vertical="center")
            sf_cell.border = _BORDER
            
            # Description cell
            ws.cell(curr_row, 4).border = _BORDER
            ws.cell(curr_row, 4).alignment = Alignment(horizontal="left", vertical="center")
            
    # Set column widths
    ws.column_dimensions["A"].width = 3
    ws.column_dimensions["B"].width = 32
    ws.column_dimensions["C"].width = 16
    ws.column_dimensions["D"].width = 50
