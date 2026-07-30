
# -*- coding: utf-8 -*-
"""
parse_cc.py
===========
Parses Kotak Mojo RuPay CC statement PDFs (pdfplumber).

Public API
----------
parse_all_statements(cc_dir, fy_start, fy_end)
    -> (cc_df: DataFrame, metas: list[dict])

cc_df columns:
    TX_Date, Particulars, Merchant, CC_Category,
    Auto_Narration, Account_Head, DR, CR,
    Statement_Period, Pay_By, Source
"""

from __future__ import annotations

import pathlib
import re
import warnings
from datetime import datetime, date

import pandas as pd
import pdfplumber

from narration_engine.cc_category_map import map_category

# ── CC spend categories that appear in Kotak statements ──────────────────────
_CC_CATEGORIES = [
    "DepartmentalStore",
    "ConsumerDurable",
    "DirectMarketing",
    "OtherMerchants",
    "TravelAgencies",
    "Entertainment",
    "Restaurants",
    "Automotive",
    "Commercial",
    "Recreation",
    "Stationery",
    "Healthcare",
    "Railroads",
    "Education",
    "Insurance",
    "Utilities",
    "Apparels",
    "Hardware",
    "Jewelry",
    "Medical",
    "Telecom",
    "Grocery",
    "Airline",
    "Computer",
    "Hotels",
    "Travel",
    "Services",
    "Fuel",
]
_CC_CATEGORIES = sorted(_CC_CATEGORIES, key=len, reverse=True)
_CAT_PAT = "|".join(re.escape(c) for c in _CC_CATEGORIES)

# ── Line-level regexes ────────────────────────────────────────────────────────

# Retail / cash purchase line:
#   20/09/2025  UPI-526304984797-KRSCULINARY   Entertainment   1,000.00
#   20/09/2025  AMAZON 356   Services   2.00 Cr
_TX_RE = re.compile(
    rf"^(\d{{2}}/\d{{2}}/\d{{4}})\s+(.+?)\s+({_CAT_PAT})\s+([\d,]+\.\d{{2}})\s*(Cr)?$",
    re.IGNORECASE,
)

# Payment / credit line (DP015… Cr):
#   21/09/2025  DP015264095741OGZVC8   1,007.00 Cr
_PMT_RE = re.compile(
    r"^(\d{2}/\d{2}/\d{4})\s+(DP\w+)\s+([\d,]+\.\d{2})\s+Cr$"
)

# Statement header regexes
_STMT_DATE_RE = re.compile(r"StatementDate\s+(\d{2}-\w{3}-\d{4})")
_PERIOD_RE    = re.compile(r"from\s+(\d{2}-\w{3}-\d{4})\s+to\s+(\d{2}-\w{3}-\d{4})")
_PAY_BY_RE    = re.compile(r"Remembertopayby\s+(\d{2}-\w{3}-\d{4})")
_TAD_RE       = re.compile(r"TotalAmountDue\(TAD\)\s+Rs\.([\d,]+\.\d{2})")


# ── Helpers ───────────────────────────────────────────────────────────────────

def _parse_date(s: str) -> datetime | None:
    for fmt in ("%d/%m/%Y", "%d-%b-%Y"):
        try:
            return datetime.strptime(s.strip(), fmt)
        except ValueError:
            pass
    return None


def _parse_amount(s: str) -> float:
    try:
        return float(s.replace(",", ""))
    except ValueError:
        return 0.0


def _extract_merchant(particulars: str) -> str:
    """Pull human-readable merchant from UPI reference or return as-is."""
    m = re.match(r"UPI-\d+-(.+)", particulars)
    if m:
        return m.group(1).strip().title()
    return particulars.strip()


# ── Per-PDF parser ────────────────────────────────────────────────────────────

def _parse_statement(pdf_path: pathlib.Path) -> tuple[dict | None, pd.DataFrame | None]:
    """
    Parse a single CC statement PDF.
    Returns (meta_dict, transactions_df).
    Returns (None, None) if the PDF cannot be identified as a valid statement.
    """
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        with pdfplumber.open(pdf_path) as pdf:
            full_text = "\n".join(
                (page.extract_text() or "") for page in pdf.pages
            )

    # ── Extract metadata ──────────────────────────────────────────────────────
    period_m   = _PERIOD_RE.search(full_text)
    if not period_m:
        return None, None  # Not a recognisable statement

    period_start = _parse_date(period_m.group(1))
    period_end   = _parse_date(period_m.group(2))
    if not period_start or not period_end:
        return None, None

    stmt_date_m = _STMT_DATE_RE.search(full_text)
    pay_by_m    = _PAY_BY_RE.search(full_text)
    tad_m       = _TAD_RE.search(full_text)

    stmt_date = _parse_date(stmt_date_m.group(1)) if stmt_date_m else None
    pay_by    = _parse_date(pay_by_m.group(1))    if pay_by_m    else None
    tad       = _parse_amount(tad_m.group(1))     if tad_m       else 0.0

    meta = {
        "period_start" : period_start,
        "period_end"   : period_end,
        "stmt_date"    : stmt_date,
        "pay_by"       : pay_by,
        "tad"          : tad,
        "pdf_path"     : str(pdf_path),
    }

    # ── Parse transaction lines ───────────────────────────────────────────────
    rows: list[dict] = []
    period_label = (
        f"{period_start.strftime('%b-%Y')} to {period_end.strftime('%b-%Y')}"
    )

    for raw_line in full_text.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        # Retail / cash purchase
        m = _TX_RE.match(line)
        if m:
            tx_date     = _parse_date(m.group(1))
            particulars = m.group(2).strip()
            cc_cat      = m.group(3)
            amount      = _parse_amount(m.group(4))
            is_cr       = bool(m.group(5))
            merchant    = _extract_merchant(particulars)
            narration, acct_head = map_category(cc_cat)

            # Airtel amount-based override (WiFi vs Telecom)
            if "airtel" in merchant.lower():
                if amount in (588.82, 406.71, 513.21):
                    narration = "CC - Wifi"
                    acct_head = "Utilities"
                else:
                    narration = "CC - Telecom"
                    acct_head = "Utilities"

            rows.append({
                "TX_Date"          : tx_date,
                "Particulars"      : particulars,
                "Merchant"         : merchant,
                "CC_Category"      : cc_cat,
                "Auto_Narration"   : narration,
                "Account_Head"     : acct_head,
                "DR"               : 0.0  if is_cr else amount,
                "CR"               : amount if is_cr else 0.0,
                "Statement_Period" : period_label,
                "Pay_By"           : pay_by,
                "Source"           : "CC_TX",
            })
            continue

        # Payment / DP credit line — skip, not a spend
        if _PMT_RE.match(line):
            continue

    df = pd.DataFrame(rows) if rows else pd.DataFrame()
    return meta, df


# ── Public API ────────────────────────────────────────────────────────────────

def parse_all_statements(
    cc_dir: str | pathlib.Path,
    fy_start: datetime,
    fy_end:   datetime,
) -> tuple[pd.DataFrame, list[dict]]:
    """
    Parse all CC statement PDFs in cc_dir.

    Steps:
      1. Parse each PDF.
      2. Deduplicate by (period_start, period_end) — prefer the PDF that has
         a valid StatementDate header (drops the duplicate March).
      3. Exclude any statement whose period is entirely outside [fy_start, fy_end].
      4. Apply FY filter to individual TX_Date rows (handles the April 2026
         statement partially — keeps Mar 21-31 rows, drops Apr 1-20).

    Returns
    -------
    cc_df : DataFrame
        All in-FY CC spend transactions with columns:
        TX_Date, Particulars, Merchant, CC_Category, Auto_Narration,
        Account_Head, DR, CR, Statement_Period, Pay_By, Source
    metas : list[dict]
        Statement-level metadata (one dict per unique statement period).
    """
    cc_dir = pathlib.Path(cc_dir)
    pdfs   = sorted(cc_dir.glob("*.pdf"))

    # Step 1 & 2: parse + deduplicate
    seen: dict[tuple, dict] = {}      # period_key -> meta
    dfs:  dict[tuple, pd.DataFrame] = {}

    for pdf_path in pdfs:
        meta, df = _parse_statement(pdf_path)
        if meta is None:
            continue
        key = (meta["period_start"], meta["period_end"])

        if key in seen:
            # Keep the one that has a valid stmt_date
            if meta["stmt_date"] is not None and seen[key]["stmt_date"] is None:
                seen[key] = meta
                dfs[key]  = df
            # else: discard the new duplicate
        else:
            seen[key] = meta
            dfs[key]  = df

    # Step 3 & 4: FY filter
    metas: list[dict] = []
    all_dfs: list[pd.DataFrame] = []

    for key, meta in seen.items():
        period_start: datetime = meta["period_start"]
        period_end:   datetime = meta["period_end"]

        # Drop statement entirely if its period ends before FY start
        # or starts after FY end
        if period_end < fy_start or period_start > fy_end:
            continue

        df = dfs.get(key, pd.DataFrame())
        if not df.empty:
            # Apply row-level FY filter on TX_Date
            mask = (df["TX_Date"] >= fy_start) & (df["TX_Date"] <= fy_end)
            df = df[mask].copy()

        metas.append(meta)
        if not df.empty:
            all_dfs.append(df)

    if not all_dfs:
        return pd.DataFrame(), metas

    cc_df = pd.concat(all_dfs, ignore_index=True)
    cc_df["TX_Date"] = pd.to_datetime(cc_df["TX_Date"])
    cc_df = cc_df.sort_values("TX_Date").reset_index(drop=True)
    return cc_df, metas


def parse_all_statements_from_cache(
    cache_path: str | pathlib.Path,
) -> tuple[pd.DataFrame, list[dict]]:
    """
    Load pre-extracted CC statements from Excel cache.
    
    This is much faster than parse_all_statements() which re-parses PDFs.
    Use this if the cache file has already been generated via
    extract_cc_statements_to_excel.py.
    
    Parameters
    ----------
    cache_path : str or Path
        Path to the CC_Statements_Cache_<FY>.xlsx file
    
    Returns
    -------
    cc_df : DataFrame
        Transaction DataFrame with columns:
        TX_Date, Particulars, Merchant, CC_Category, Auto_Narration,
        Account_Head, DR, CR, Statement_Period, Pay_By, Source
    metas : list[dict]
        Statement-level metadata (one dict per statement period)
    """
    cache_path = pathlib.Path(cache_path)
    
    if not cache_path.exists():
        return pd.DataFrame(), []
    
    # Load transactions
    try:
        cc_df = pd.read_excel(cache_path, sheet_name="Transactions")
        # Convert date columns back to datetime
        cc_df["TX_Date"] = pd.to_datetime(cc_df["TX_Date"])
        cc_df["Pay_By"] = pd.to_datetime(cc_df["Pay_By"], errors="coerce")
    except Exception as e:
        warnings.warn(f"Could not load transactions from cache: {e}")
        cc_df = pd.DataFrame()
    
    # Load metadata
    try:
        metas_df = pd.read_excel(cache_path, sheet_name="Metadata")
        metas = []
        for _, row in metas_df.iterrows():
            meta = {
                "period_start": pd.Timestamp(row["Period_Start"]).to_pydatetime() if pd.notna(row["Period_Start"]) else None,
                "period_end": pd.Timestamp(row["Period_End"]).to_pydatetime() if pd.notna(row["Period_End"]) else None,
                "stmt_date": pd.Timestamp(row["Statement_Date"]).to_pydatetime() if pd.notna(row["Statement_Date"]) else None,
                "pay_by": pd.Timestamp(row["Pay_By"]).to_pydatetime() if pd.notna(row["Pay_By"]) else None,
                "tad": float(row["Total_Amount_Due"]) if pd.notna(row["Total_Amount_Due"]) else 0.0,
                "pdf_path": str(row["PDF_Path"]) if pd.notna(row["PDF_Path"]) else "",
            }
            metas.append(meta)
    except Exception as e:
        warnings.warn(f"Could not load metadata from cache: {e}")
        metas = []
    
    return cc_df, metas


# ── CLI test helper ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    cc_dir   = pathlib.Path(r"E:\Tax\credit_card_statements")
    fy_start = datetime(2025, 4, 1)
    fy_end   = datetime(2026, 3, 31)

    print("Parsing CC statements …")
    cc_df, metas = parse_all_statements(cc_dir, fy_start, fy_end)

    print(f"\n{len(metas)} statements loaded, {len(cc_df)} spend rows in FY26\n")
    print("=== Statement summary ===")
    for m in sorted(metas, key=lambda x: x["period_start"]):
        df_rows = cc_df[cc_df["Statement_Period"].str.startswith(
            m["period_start"].strftime("%b-%Y")
        )]
        spend_total = df_rows["DR"].sum()
        print(
            f"  {m['period_start'].strftime('%d-%b-%Y')} -> "
            f"{m['period_end'].strftime('%d-%b-%Y')}  "
            f"TAD={m['tad']:,.2f}  "
            f"Parsed DR={spend_total:,.2f}  "
            f"PayBy={m['pay_by'].strftime('%d-%b-%Y') if m['pay_by'] else '?'}"
        )

    print("\n=== Category breakdown (FY26 totals) ===")
    if not cc_df.empty:
        cat_totals = (
            cc_df[cc_df["DR"] > 0]
            .groupby("Auto_Narration")["DR"]
            .sum()
            .sort_values(ascending=False)
        )
        for cat, total in cat_totals.items():
            print(f"  {cat:<30}  Rs.{total:>10,.2f}")
        print(f"\n  {'TOTAL':<30}  Rs.{cat_totals.sum():>10,.2f}")
