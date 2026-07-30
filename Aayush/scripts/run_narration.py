# -*- coding: utf-8 -*-
"""
run_narration.py
================
Generalised multi-bank narration automator.

Usage:
    python run_narration.py [--fy FY25] [--input PATH] [--output PATH]

Defaults (derived from --fy):
    --input  : e:\Tax\Aayush\Bank Statements\FY26\Aayush Acct_Statement_XXXXXXXX5413_14042026.xlsx
    --output : e:\Tax\Aayush\Generated Data\<FY>\Aayush_Consolidated_Bank_Ledger_<FY>.xlsx

Author  : Aayush Gupta
Version : 2.0  (generalised engine — replaces axis/hdfc/kotak_narration_automator.py)
"""

from __future__ import annotations
import sys
import io
import re
import argparse
import importlib
import logging
import warnings
from pathlib import Path
from datetime import datetime

import pandas as pd
from openpyxl import load_workbook, Workbook

# ── Logger initialization ────────────────────────────────────────────────────
logger = logging.getLogger("run_narration")

# ── Force UTF-8 output on Windows ────────────────────────────────────────────
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

# ── Engine imports ────────────────────────────────────────────────────────────
from narration_engine.auto_header    import find_header_row
from narration_engine.bank_identifier import identify_bank
from narration_engine.bank_registry  import BANK_REGISTRY, OUTPUT_SHEET_NAMES
from narration_engine.classifier     import classify
from narration_engine.exporter import (
    write_bank_sheet, write_for_tally, write_conso, write_bank_summary,
    write_monthly_pivot, write_colour_legend, write_cc_sheet,
    COLOUR_MAP, assign_pivot_categories,
)
from narration_engine.parse_cc import (
    parse_all_statements as parse_cc_statements,
    parse_all_statements_from_cache as parse_cc_from_cache,
)

# ── Defaults ──────────────────────────────────────────────────────────────────
_BASE = Path(r"E:\Tax\Aayush\Generated Data")


def _default_input(fy: str) -> Path:
    base = _BASE / fy
    # Try exact match first
    exact = base / f"All Bank Statements Aayush {fy}.xlsx"
    if exact.exists():
        return exact
    # Glob for any "All Bank Statements*.xlsx" in the FY folder
    matches = list(base.glob("All Bank Statements*.xlsx"))
    if matches:
        return matches[0]
    return exact  # will trigger "not found" error with a clear path

def _default_output(fy: str) -> Path:
    return _BASE / fy / f"Aayush_Consolidated_Bank_Ledger_{fy}.xlsx"


# ── Sheet Parser ──────────────────────────────────────────────────────────────

def _find_col(df: pd.DataFrame, col_name: str | None) -> str | None:
    """Find a column by exact name, then case-insensitive, then partial."""
    if col_name is None:
        return None
    if col_name in df.columns:
        return col_name
    lower = {c.lower(): c for c in df.columns}
    if col_name.lower() in lower:
        return lower[col_name.lower()]
    # Partial match
    for c in df.columns:
        if col_name.lower() in c.lower():
            return c
    return None


def _compute_dr_cr_from_amount(df: pd.DataFrame) -> pd.DataFrame:
    """
    If DR/CR columns are missing but Amount + Dr/Cr indicator columns exist,
    split Amount into DR and CR.
    """
    amount_col = _find_col(df, "Amount")
    drcr_col   = _find_col(df, "Dr / Cr")
    if amount_col and drcr_col:
        df["Amount"] = pd.to_numeric(df[amount_col], errors="coerce").fillna(0)
        df["DR"] = df.apply(
            lambda r: r["Amount"] if str(r[drcr_col]).strip().upper() == "DR" else 0, axis=1)
        df["CR"] = df.apply(
            lambda r: r["Amount"] if str(r[drcr_col]).strip().upper() == "CR" else 0, axis=1)
    return df


# ── Beneficiary Extractor ──────────────────────────────────────────────────────

_UPI_BENE_PATTERNS = [
    # Axis:  UPI/P2M/<ref>/<NAME            >/<bank_hint>/<bank>
    # Axis:  UPI/P2A/<ref>/<NAME            >/<bank_hint>/
    (re.compile(r"^UPI/P2[AM]/\d+/([^/]+)/", re.IGNORECASE), 1),
    # Kotak: UPI/<NAME>/<ref>/<remark>
    (re.compile(r"^UPI/([^/]+)/\d+/", re.IGNORECASE), 1),
    # SBI:   WDL TFR   UPI/DR/<ref>/<NAME>/<BANK>/<VPA>/<remark>
    (re.compile(r"UPI/(?:DR|CR)/\d+/([^/]+)/", re.IGNORECASE), 1),
    # HDFC:  UPI-<NAME>-<VPA>-<BANK>-<ref>-<remark>
    (re.compile(r"^UPI-([^-]+)-", re.IGNORECASE), 1),
]


def _extract_beneficiary(particulars: str, auto_narration: str) -> str:
    """
    For low-confidence UPI transactions, extract the human-readable beneficiary
    name from the raw particulars string so reviewers can identify P2P payments.
    Returns empty string for high-confidence classified transactions.
    """
    # Only add beneficiary for generic UPI Payment/Receipt — not named merchants
    if auto_narration not in ("UPI Payment", "UPI Receipt"):
        return ""
    p = str(particulars).strip()
    for pat, grp in _UPI_BENE_PATTERNS:
        m = pat.search(p)
        if m:
            name = m.group(grp).strip()
            # Skip if it looks like a VPA (contains @) or pure digits
            if "@" not in name and not name.isdigit() and len(name) > 1:
                return name.title()   # Title-case: "NANDINI" → "Nandini"
    return ""


# ── Sheet Parser ──────────────────────────────────────────────────────

def parse_sheet(wb_path: str, sheet_name: str) -> tuple[pd.DataFrame, str, float, dict]:
    """
    Parse one bank sheet from the workbook.

    Returns
    -------
    (df, bank_key, match_score, bank_cfg)
    df contains standardised columns: Date, Particulars, Ref, DR, CR, Balance,
    Value_Date, Human_Narration, TX_Date
    """
    # Read raw rows for fingerprinting / header detection
    wb_raw = load_workbook(wb_path, read_only=True, data_only=True)
    ws_raw = wb_raw[sheet_name]
    raw_rows = list(ws_raw.iter_rows(values_only=True))
    wb_raw.close()

    hdr_idx    = find_header_row(raw_rows)
    bank_key, score = identify_bank(raw_rows, hdr_idx)

    # ── Special override: FEDERAL sheet has deep metadata (18 rows before header) ──
    # If still unknown, scan ALL rows for FEDERAL-specific signals
    if bank_key == "unknown":
        all_text = " ".join(
            str(c).strip() for row in raw_rows for c in row
            if c is not None and str(c).strip() not in ("", "nan", "none")
        ).lower()
        federal_signals = ["fdrl0007777", "77770101840847", "salary-7777",
                           "neo banking", "jupiter"]
        if sum(1 for sig in federal_signals if sig in all_text) >= 2:
            bank_key = "federal"
            score    = 0.80
            # Re-scan for header using all rows (Federal header is at row 18)
            hdr_idx = find_header_row(raw_rows)
            # If auto-detect still wrong, find first row with 'Tran Type' or 'Tran ID'
            for i, row in enumerate(raw_rows):
                cells_lower = [str(c).strip().lower() for c in row if c is not None]
                if "tran type" in cells_lower or "tran id" in cells_lower:
                    hdr_idx = i
                    break

    cfg = BANK_REGISTRY.get(bank_key, {})

    # Read with pandas using detected header row
    df = pd.read_excel(wb_path, sheet_name=sheet_name, header=hdr_idx)
    df.columns = [str(c).strip() for c in df.columns]

    # Handle duplicate column names (e.g. HDFC "Narration" appears twice)
    seen: dict[str, int] = {}
    new_cols = []
    for c in df.columns:
        if c in seen:
            seen[c] += 1
            new_cols.append(f"{c}.{seen[c]}")
        else:
            seen[c] = 0
            new_cols.append(c)
    df.columns = new_cols

    # Ensure DR / CR columns exist
    if "DR" not in df.columns or "CR" not in df.columns:
        df = _compute_dr_cr_from_amount(df)

    # Resolve column names via config
    def col(key):
        name = cfg.get(key)
        if isinstance(name, list):
            for n in name:
                res = _find_col(df, n)
                if res is not None:
                    return res
            return None
        return _find_col(df, name)

    date_col        = col("col_date")
    particulars_col = col("col_particulars")
    human_narr_col  = col("col_narration_h")
    dr_col          = col("col_dr")   or _find_col(df, "DR")
    cr_col          = col("col_cr")   or _find_col(df, "CR")
    balance_col     = col("col_balance")
    ref_col         = col("col_ref")
    vdate_col       = col("col_value_date")

    # For HDFC: Narration appears twice; particulars is the FIRST, human narration is ".1"
    if bank_key == "hdfc":
        if "Narration" in df.columns and "Narration.1" in df.columns:
            particulars_col  = "Narration"
            human_narr_col   = "Narration.1"
        else:
            particulars_col  = "Narration" if "Narration" in df.columns else particulars_col
            human_narr_col   = None
        if "Withdrawal Amt." in df.columns:
            dr_col = "Withdrawal Amt."
        if "Deposit Amt." in df.columns:
            cr_col = "Deposit Amt."

    # Drop rows where Particulars is completely empty / NaN
    if particulars_col:
        df = df[df[particulars_col].notna() &
                (df[particulars_col].astype(str).str.strip().str.lower() != "nan")]
        df = df.reset_index(drop=True)

    # Coerce numerics
    if dr_col:
        df[dr_col] = pd.to_numeric(df[dr_col], errors="coerce").fillna(0)
    if cr_col:
        df[cr_col] = pd.to_numeric(df[cr_col], errors="coerce").fillna(0)

    # Build standardised output frame
    out = pd.DataFrame()
    out["TX_Date"]         = df[date_col]        if date_col        else None
    out["Value_Date"]      = df[vdate_col]        if vdate_col       else out["TX_Date"]
    out["Particulars"]     = df[particulars_col]  if particulars_col else ""
    out["Ref"]             = df[ref_col]          if ref_col         else ""
    out["DR"]              = df[dr_col]           if dr_col          else 0.0
    out["CR"]              = df[cr_col]           if cr_col          else 0.0
    out["Balance"]         = df[balance_col]      if balance_col     else None
    out["Human_Narration"] = (df[human_narr_col]  if human_narr_col  else "")

    # Normalise TX_Date to datetime at parse time.
    # dayfirst=True is critical for banks (e.g. SBI) that store dates as
    # DD/MM/YYYY strings — without it pandas mis-reads '02/04/2025' as Feb 4
    # instead of Apr 2, scattering transactions into the wrong months.
    out["TX_Date"] = pd.to_datetime(out["TX_Date"], errors="coerce", dayfirst=True)
    out["Value_Date"] = pd.to_datetime(out["Value_Date"], errors="coerce", dayfirst=True)
    out["Bank_Key"]        = bank_key
    out["Bank_Display"]    = cfg.get("display_name", bank_key.upper())
    out["Account_ID"]      = cfg.get("account_id", sheet_name)
    # Filter out rows where both DR and CR are zero or empty (noise/headers/separators)
    out = out[(out["DR"] > 0) | (out["CR"] > 0)]
    out = out.reset_index(drop=True)

    # Classify
    results = out.apply(
        lambda r: classify(r["Particulars"], r["DR"], r["CR"], bank_key),
        axis=1, result_type="expand"
    )
    out["Auto_Narration"] = results[0]
    out["Account_Head"]   = results[1]
    out["Confidence"]     = results[2].round(2)

    # Beneficiary: extract payee name for generic UPI Payment/Receipt rows
    out["Beneficiary"] = out.apply(
        lambda r: _extract_beneficiary(r["Particulars"], r["Auto_Narration"]),
        axis=1
    )

    # Promote UPI Receipt + extracted name → "Received - {Name}"
    # This mirrors the "Transfer - Sunita Gupta" pattern for inbound UPI transfers.
    receipt_with_name = (
        (out["Auto_Narration"] == "UPI Receipt") &
        (out["Beneficiary"].str.strip() != "")
    )
    out.loc[receipt_with_name, "Auto_Narration"] = (
        "Received - " + out.loc[receipt_with_name, "Beneficiary"]
    )
    # Name is now in Auto_Narration, so clear Beneficiary for those rows
    out.loc[receipt_with_name, "Beneficiary"] = ""

    # Also promote family transfers (e.g. "Transfer - Sunita Gupta") to "Received - Sunita Gupta" if it is an inflow (CR > 0)
    family_receipt = (
        out["Auto_Narration"].str.startswith("Transfer - ") &
        (out["CR"] > 0)
    )
    if family_receipt.any():
        out.loc[family_receipt, "Auto_Narration"] = (
            out.loc[family_receipt, "Auto_Narration"].str.replace("Transfer - ", "Received - ", regex=False)
        )

    # Match vs human narration
    if human_narr_col:
        out["Match"] = out.apply(
            lambda r: _match(r["Human_Narration"], r["Auto_Narration"], r["Account_Head"]),
            axis=1
        )
    else:
        out["Match"] = "N/A"

    # Opening / Closing balance
    balance_series = out["Balance"].dropna()
    if not balance_series.empty:
        bal_num = pd.to_numeric(balance_series, errors="coerce").dropna()
        closing  = float(bal_num.iloc[-1])  if len(bal_num) > 0 else 0.0
        # Opening = closing of first row adjusted back
        first_dr = float(out["DR"].iloc[0]) if len(out) > 0 else 0.0
        first_cr = float(out["CR"].iloc[0]) if len(out) > 0 else 0.0
        first_bal = float(pd.to_numeric(bal_num.iloc[0], errors="coerce")) if len(bal_num) > 0 else 0.0
        opening = first_bal + first_dr - first_cr
    else:
        opening = closing = 0.0

    return out, bank_key, score, {
        "opening": opening, "closing": closing,
        "cfg": cfg, "sheet_name": sheet_name
    }


# ── Match logic ───────────────────────────────────────────────────────────────
# Maps raw human narration labels to sets of acceptable Auto_Narration values

_MATCH_GROUPS: dict[str, set[str]] = {
    "HSL"             : {"HDFC Securities - Buy", "HDFC Securities - Sell",
                         "HDFC Securities - Settlement", "HDFC Securities"},
    "Ye kya hai?"     : {"HDFC Securities - Settlement"},
    "SIP - 5000"      : {"SIP"},
    "SIP - 7000"      : {"SIP"},
    "SIP - 10000"     : {"SIP"},
    "SIP?"            : {"SIP"},
    "SIP"             : {"SIP"},
    "Mutual Fund"     : {"SIP", "MF Redemption", "MF Refund / Reversal"},
    "Sale of MF"      : {"MF Redemption"},
    "Sale of MF??"    : {"MF Redemption"},
    "Redemption"      : {"MF Redemption"},
    "Personal"        : {"UPI Payment", "UPI Receipt", "Card Purchase",
                         "Cash Withdrawal", "IMPS Receipt",
                         "MF Refund / Reversal", "Cheque"},
    "UPI"             : {"UPI Payment", "UPI Receipt", "UPI Reversal",
                         "Zerodha Broking", "Transfer - Archit Gupta",
                         "Transfer - Ajay Gupta", "Transfer - Sunita Gupta",
                         "Rent", "Card Purchase", "Cash Withdrawal",
                         "Credit Card Payment", "MF Refund / Reversal",
                         "IMPS Receipt", "Misc Income", "NEFT Transfer",
                         "Contra - SBI", "Contra - Jupiter",
                         "Contra - Jupiter (Inward)", "Contra - Kotak",
                         "Dividend Income", "Bank Interest", "SIP",
                         "Auto Sweep FD", "Insurance Premium"} | {
                         k for k in COLOUR_MAP if k.startswith("UPI - ")},
    "UPI - ZOMATO"    : {"UPI - Zomato"},
    "Contra - KOTAK"  : {"Contra - Kotak"},
    "Contra - SBI"    : {"Contra - SBI"},
    "Contra - Jupiter": {"Contra - Jupiter", "Contra - Jupiter (Inward)"},
    "CDSL?"           : {"Depository Credit"},
    "What is this?"   : {"What is this?"},
    "??"              : {"What is this?", "Insurance Premium"},
    "ATM Withdrawal"  : {"Cash Withdrawal"},
    "Transfer to Sunita"  : {"Transfer - Sunita Gupta"},
    "Transfer from Sunita": {"Transfer - Sunita Gupta"},
    "Transfer to Ajay"    : {"Transfer - Ajay Gupta"},
    "Transfer from Ajay"  : {"Transfer - Ajay Gupta"},
    "Transfer to Archit"  : {"Transfer - Archit Gupta"},
    "Transfer from Archit": {"Transfer - Archit Gupta"},
    "Transfer from Archit": {"Transfer - Archit Gupta"},
}

def _match(human: str, auto_narr: str, auto_head: str) -> str:
    h = str(human).strip()
    if h.lower() in ("nan", "none", ""):
        return "N/A"
    # Direct label match (case-insensitive)
    if h.lower() == auto_narr.lower() or h.lower() == auto_head.lower():
        return "[MATCH]"
    # Group-based match
    allowed = _MATCH_GROUPS.get(h, set())
    if auto_narr in allowed:
        return "[MATCH]"
    return "[DIFF]"


# ── Console reporting ─────────────────────────────────────────────────────────

def _print_bank_report(sheet_name: str, bank_key: str, score: float,
                       display: str, df: pd.DataFrame):
    total   = len(df)
    matches = (df["Match"] == "[MATCH]").sum()
    diffs   = (df["Match"] == "[DIFF]").sum()
    nas     = (df["Match"] == "N/A").sum()
    acc     = matches / (total - nas) * 100 if (total - nas) > 0 else 0

    h_conf  = (df["Confidence"] >= 0.85).sum()
    m_conf  = ((df["Confidence"] >= 0.60) & (df["Confidence"] < 0.85)).sum()
    l_conf  = (df["Confidence"] < 0.60).sum()

    logger.info(f"\n  {'─'*62}")
    logger.info(f"  Sheet    : {sheet_name}  →  {display}  (match score: {score:.2f})")
    logger.info(f"  Total    : {total}  |  Matched: {matches} ({acc:.1f}%)  |  Diff: {diffs}")
    logger.info(f"  Confidence → High: {h_conf}  Medium: {m_conf}  Low: {l_conf}")
    logger.info(f"  DR total : ₹{df['DR'].sum():>14,.2f}   CR total: ₹{df['CR'].sum():>14,.2f}")

    # Top 5 "What is this?" rows
    wits = df[df["Auto_Narration"] == "What is this?"].head(5)
    if not wits.empty:
        logger.info(f"\n  Top 'What is this?' entries:")
        for _, r in wits.iterrows():
            logger.info(f"    [{r['DR']:>10,.2f} DR / {r['CR']:>10,.2f} CR]  {str(r['Particulars'])[:70]}")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Multi-bank narration automator")
    parser.add_argument("--fy",       default="FY25",  help="Financial year tag, e.g. FY25")
    parser.add_argument("--input",    default=None,    help="Path to input workbook")
    parser.add_argument("--output",   default=None,    help="Path for output workbook")
    parser.add_argument("--cc-dir",   default=r"E:\Tax\Aayush\credit_card_statements",
                        help="Directory containing Kotak CC statement PDFs")
    parser.add_argument("--skip-cc",  action="store_true",
                        help="Skip credit card statement parsing")
    parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"], help="Set the logging level")
    parser.add_argument("--log-file",  default=None,   help="Path to the log file")
    args = parser.parse_args()

    input_path  = Path(args.input)  if args.input  else _default_input(args.fy)
    output_path = Path(args.output) if args.output else _default_output(args.fy)
    fy_label    = args.fy
    cc_dir      = Path(args.cc_dir)
    skip_cc     = args.skip_cc

    # ── Logging Configuration ──────────────────────────────────────────────────
    if args.log_file:
        log_file_path = Path(args.log_file)
    else:
        log_file_path = output_path.parent / "run_narration.log"

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)

    # Suppress verbose debug logs from third-party libraries
    logging.getLogger("pdfminer").setLevel(logging.WARNING)
    logging.getLogger("pdfplumber").setLevel(logging.WARNING)
    logging.getLogger("openpyxl").setLevel(logging.WARNING)
    logging.getLogger("PIL").setLevel(logging.WARNING)

    # Clean existing handlers
    for h in list(root_logger.handlers):
        root_logger.removeHandler(h)

    # 1. Console Handler
    console_handler = logging.StreamHandler(sys.stdout)
    numeric_level = getattr(logging, args.log_level.upper(), logging.INFO)
    console_handler.setLevel(numeric_level)

    # Custom formatter to keep console output clean like standard prints
    class ConsoleFormatter(logging.Formatter):
        def format(self, record):
            if record.levelno >= logging.WARNING:
                return f"[{record.levelname}] {record.getMessage()}"
            return record.getMessage()

    console_handler.setFormatter(ConsoleFormatter())

    # Suppress captured python warnings from the console, unless log level is DEBUG
    class SuppressWarningsFilter(logging.Filter):
        def filter(self, record):
            if record.name == "py.warnings" and numeric_level > logging.DEBUG:
                return False
            return True
    console_handler.addFilter(SuppressWarningsFilter())
    root_logger.addHandler(console_handler)

    # 2. File Handler
    try:
        log_file_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file_path, encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter('%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s')
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)
    except Exception as e:
        logger.warning(f"Could not create log file at {log_file_path}: {e}")

    # Capture standard python warnings and redirect to logging
    logging.captureWarnings(True)

    try:
        logger.info(f"\n{'='*65}")
        logger.info(f"  NARRATION AUTOMATOR  v2.0")
        logger.info(f"  Generated : {datetime.now().strftime('%d-%b-%Y %H:%M:%S')}")
        logger.info(f"  FY        : {fy_label}")
        logger.info(f"  Input     : {input_path}")
        logger.info(f"  Output    : {output_path}")
        logger.info(f"{'='*65}")

        if not input_path.exists():
            logger.error(f"Input file not found: {input_path}")
            sys.exit(1)

        # Detect bank sheets
        wb_probe = load_workbook(input_path, read_only=True)
        all_sheet_names = wb_probe.sheetnames
        wb_probe.close()
        bank_sheets = [s for s in all_sheet_names if s not in OUTPUT_SHEET_NAMES]

        logger.info(f"\n  Sheets found     : {all_sheet_names}")
        logger.info(f"  Processing sheets: {bank_sheets}")
        logger.info(f"\n  {'Sheet':<15} {'Identified As':<30} {'Match Score'}")
        logger.info(f"  {'─'*15} {'─'*30} {'─'*12}")

        # Parse all bank sheets
        bank_dfs: list[pd.DataFrame] = []
        bank_balances: dict[str, tuple[float, float]] = {}
        sheet_meta: list[tuple] = []

        for sname in bank_sheets:
            try:
                df, bkey, score, meta = parse_sheet(str(input_path), sname)
                display = meta["cfg"].get("display_name", bkey)
                logger.info(f"  {sname:<15} {display:<30} {score:.3f}")
                bank_dfs.append(df)
                acct_id = meta["cfg"].get("account_id", sname)
                bank_balances[acct_id] = (meta["opening"], meta["closing"])
                sheet_meta.append((sname, bkey, score, display, df))
            except Exception as exc:
                logger.warning(f"Could not process sheet '{sname}': {exc}")

        if not bank_dfs:
            logger.error("No bank sheets could be processed.")
            sys.exit(1)

        # ── Cross-bank matching of self-transfers (Contra) ────────────────────
        logger.info("  Post-processing cross-bank self-transfers...")
        all_tx_list = []
        for df in bank_dfs:
            bkey = df["Bank_Key"].iloc[0] if not df.empty else "unknown"
            for idx, row in df.iterrows():
                p = str(row["Particulars"])
                # Extract 12-digit RRN
                rrn = None
                m = re.search(r"(?:\b|/|-)(\d{12})(?:\b|/|-)", p)
                if m:
                    rrn = m.group(1)
                else:
                    m = re.search(r"\b(\d{12})\b", p)
                    if m:
                        rrn = m.group(1)
                
                all_tx_list.append({
                    "df_ref": df,
                    "idx": idx,
                    "Bank_Key": bkey,
                    "Date": row["TX_Date"],
                    "Particulars": p,
                    "DR": float(row["DR"]) if pd.notna(row["DR"]) else 0.0,
                    "CR": float(row["CR"]) if pd.notna(row["CR"]) else 0.0,
                    "Auto_Narration": str(row["Auto_Narration"]),
                    "Account_Head": str(row["Account_Head"]),
                    "RRN": rrn
                })

        BANK_SHORT_NAMES = {
            "sbi": "SBI",
            "kotak": "Kotak",
            "axis": "Axis",
            "federal": "Jupiter",
            "hdfc": "HDFC",
            "sbm": "SBM"
        }
        
        updated_contras_count = 0
        for tx in all_tx_list:
            if tx["Auto_Narration"] not in ("Contra - Self", "Contra - Self (SuperMoney)"):
                continue
            
            # Find counterpart
            rrn = tx["RRN"]
            bkey = tx["Bank_Key"]
            amt = tx["DR"] if tx["DR"] > 0 else tx["CR"]
            is_dr = tx["DR"] > 0
            
            match_found = False
            counterpart = None
            
            if rrn:
                # Find by RRN in other banks
                for c_tx in all_tx_list:
                    if c_tx["RRN"] == rrn and c_tx["Bank_Key"] != bkey:
                        counterpart = c_tx
                        match_found = True
                        break
            
            if not match_found:
                # Try Date/Amount fallback (opposite DR/CR sign, within +/- 1 day)
                t_date = pd.to_datetime(tx["Date"])
                for c_tx in all_tx_list:
                    if c_tx["Bank_Key"] == bkey:
                        continue
                    # Check opposite sign
                    if is_dr and c_tx["CR"] <= 0:
                        continue
                    if not is_dr and c_tx["DR"] <= 0:
                        continue
                    # Check amount
                    c_amt = c_tx["CR"] if is_dr else c_tx["DR"]
                    if abs(c_amt - amt) > 0.05:
                        continue
                    # Check date
                    c_date = pd.to_datetime(c_tx["Date"])
                    if pd.notna(t_date) and pd.notna(c_date) and abs((c_date - t_date).days) <= 1:
                        counterpart = c_tx
                        match_found = True
                        break
            
            if match_found and counterpart:
                c_bkey = counterpart["Bank_Key"]
                short_name = BANK_SHORT_NAMES.get(c_bkey, c_bkey.upper())
                target_head = BANK_REGISTRY.get(c_bkey, {}).get("account_id", c_bkey.upper())
                
                # Update in the original DataFrame
                df = tx["df_ref"]
                idx = tx["idx"]
                
                df.at[idx, "Auto_Narration"] = f"Contra - {short_name}"
                df.at[idx, "Account_Head"] = target_head
                df.at[idx, "Confidence"] = 0.95
                
                # Promote to Received if it's a receipt and counterpart is a known bank
                # wait, let's keep Contra - <Bank Name> since it's a self transfer
                
                logger.info(f"    Resolved self-transfer in sheet '{tx['df_ref'].columns.name or bkey.upper()}' of amount {amt} on {tx['Date']} as Contra - {short_name} (counterpart in {c_bkey.upper()})")
                updated_contras_count += 1

        logger.info(f"  Successfully resolved {updated_contras_count} generic Contra/Self transactions using cross-bank matching.")

        # Combine all
        all_df = pd.concat(bank_dfs, ignore_index=True)
        # Sort by date
        all_df["_sort_date"] = pd.to_datetime(all_df["TX_Date"], errors="coerce")
        all_df = all_df.sort_values("_sort_date").drop(columns=["_sort_date"])
        all_df = all_df.reset_index(drop=True)
        
        # Assign unified categories for monthly pivot mapping
        all_df = assign_pivot_categories(all_df)

        # ── FY date-range filter ──────────────────────────────────────────────
        # FY26 = 1-Apr-2025 to 31-Mar-2026  (FY XX = 1-Apr-(XX-1) to 31-Mar-XX)
        fy_start = None
        fy_end   = None
        try:
            fy_year = int(fy_label.replace("FY", "").strip())   # e.g. 26 → 2026 or 2026
            if fy_year < 100:
                fy_year += 2000                                  # 26 → 2026
            fy_start = pd.Timestamp(year=fy_year - 1, month=4,  day=1)
            fy_end   = pd.Timestamp(year=fy_year,     month=3, day=31, hour=23, minute=59, second=59)
            all_df["_val_dt"] = pd.to_datetime(all_df["Value_Date"], errors="coerce")
            before = len(all_df)
            all_df = all_df[(all_df["_val_dt"] >= fy_start) & (all_df["_val_dt"] <= fy_end)]
            all_df = all_df.drop(columns=["_val_dt"]).reset_index(drop=True)
            trimmed = before - len(all_df)
            if trimmed:
                logger.info(f"  FY filter [{fy_start.date()} → {fy_end.date()}]: "
                            f"removed {trimmed} out-of-range transaction(s).")
        except Exception as e:
            logger.warning(f"  Could not apply FY date filter: {e}")

        # ── CC statement parsing ──────────────────────────────────────────────
        cc_df = None
        if not skip_cc and cc_dir.is_dir():
            try:
                from datetime import datetime as _dt
                _fy_start = _dt(fy_start.year, fy_start.month, fy_start.day)
                _fy_end   = _dt(fy_end.year,   fy_end.month,   fy_end.day)
                
                # Try to load from cache first (faster)
                cache_path = _BASE / fy_label / f"CC_Statements_Cache_{fy_label}.xlsx"
                if cache_path.exists():
                    logger.info(f"  Loading CC cache : {cache_path.name}")
                    cc_df, cc_metas = parse_cc_from_cache(cache_path)
                else:
                    # Fall back to PDF parsing
                    logger.info(f"  Cache not found. Parsing PDFs (this may take time)...")
                    logger.info(f"  Hint: Run 'python extract_cc_statements_to_excel.py --fy {fy_label}' for faster future runs")
                    cc_df, cc_metas = parse_cc_statements(cc_dir, _fy_start, _fy_end)
                
                if not cc_df.empty:
                    logger.info(f"  CC statements : {len(cc_metas)} loaded, "
                                f"{len(cc_df)} spend rows, "
                                f"total DR=Rs.{cc_df['DR'].sum():,.2f}")
                    # Annotate CRED bank rows with CC_Statement_Period
                    # For each CC statement, find matching CRED bank rows in the payment window
                    _cc_mask = all_df["Auto_Narration"].str.contains(
                        r"Credit Card.*Payment|Credit Card Bill", na=False, regex=True
                    )
                    all_df["CC_Statement_Period"] = ""
                    for meta in cc_metas:
                        p_start = pd.Timestamp(meta["period_start"])
                        p_end   = pd.Timestamp(meta["period_end"])
                        pay_by  = pd.Timestamp(meta["pay_by"]) if meta["pay_by"] else p_end + pd.Timedelta(days=18)
                        win_start = p_end - pd.Timedelta(days=2)   # payments start ~day before statement closes
                        period_label = f"{meta['period_start'].strftime('%b-%Y')} stmt"
                        _date_col = pd.to_datetime(all_df["TX_Date"], errors="coerce")
                        _in_window = _cc_mask & (_date_col >= win_start) & (_date_col <= pay_by)
                        all_df.loc[_in_window, "CC_Statement_Period"] = period_label
                else:
                    logger.info("  CC statements : no spend rows found in FY range")
            except Exception as cc_err:
                logger.warning(f"  CC parsing failed: {cc_err}")
        elif skip_cc:
            logger.info("  CC statements : skipped (--skip-cc)")
        else:
            logger.info(f"  CC statements : directory not found ({cc_dir}) — skipped")

        # ── Duplicate detection ───────────────────────────────────────────────

        # Flag rows where (Date, DR, CR, Auto_Narration) are identical within same bank
        dup_key = all_df[["TX_Date", "DR", "CR", "Auto_Narration", "Bank_Key"]].copy()
        dup_key["TX_Date"] = pd.to_datetime(dup_key["TX_Date"], errors="coerce").dt.date
        all_df["Duplicate"] = dup_key.duplicated(keep=False).map({True: "⚠ Possible Duplicate", False: ""})

        # Per-bank reports
        for sname, bkey, score, display, df in sheet_meta:
            _print_bank_report(sname, bkey, score, display, df)

        # Overall confidence stats
        total = len(all_df)
        logger.info(f"\n{'='*65}")
        logger.info(f"  OVERALL SUMMARY  ({total} transactions across {len(bank_dfs)} banks)")
        logger.info(f"  High confidence (≥0.85) : {(all_df['Confidence'] >= 0.85).sum()} "
                    f"({(all_df['Confidence'] >= 0.85).sum()/total*100:.1f}%)")
        logger.info(f"  Medium (0.60–0.84)      : {((all_df['Confidence'] >= 0.60) & (all_df['Confidence'] < 0.85)).sum()}")
        logger.info(f"  Low (<0.60)             : {(all_df['Confidence'] < 0.60).sum()}")
        logger.info(f"  'What is this?' count   : {(all_df['Auto_Narration'] == 'What is this?').sum()}")
        logger.info(f"{'='*65}\n")

        # ── Write output workbook ─────────────────────────────────────────────
        logger.info(f"  Writing output: {output_path}")
        out_wb = Workbook()
        out_wb.remove(out_wb.active)   # remove default blank sheet

        # Per-bank sheets
        for sname, bkey, score, display, df in sheet_meta:
            write_bank_sheet(out_wb, df, sheet_name=sname, display_name=display)

        # Summary sheets
        # Build FY date range label
        tx_dates_coerced = pd.to_datetime(all_df["TX_Date"], errors="coerce").dropna()
        if not tx_dates_coerced.empty:
            min_date = tx_dates_coerced.min()
            max_date = tx_dates_coerced.max()
            fy_range = f"{min_date.strftime('%d-%b-%Y')} to {max_date.strftime('%d-%b-%Y')}"
        else:
            fy_range = fy_label

        # Determine account holder name dynamically from folder structure
        owner_folder = Path(__file__).resolve().parent.parent.name
        name_mapping = {
            "Ajay": "Ajay Kumar Gupta",
            "Aayush": "Aayush Kumar Gupta",
            "Sunita": "Sunita Gupta"
        }
        account_holder = name_mapping.get(owner_folder, f"{owner_folder} Gupta")

        write_for_tally(out_wb, all_df)
        write_conso(out_wb, all_df, fy_range, account_holder=account_holder)
        write_bank_summary(out_wb, all_df, bank_balances, fy_range, account_holder=account_holder)
        write_monthly_pivot(out_wb, all_df, cc_df=cc_df)
        if cc_df is not None and not cc_df.empty:
            write_cc_sheet(out_wb, cc_df)
        write_colour_legend(out_wb)

        output_path.parent.mkdir(parents=True, exist_ok=True)
        out_wb.save(str(output_path))
        logger.info(f"  Saved: {output_path}\n")

    except Exception as e:
        logger.exception(f"Fatal error during narration execution: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
