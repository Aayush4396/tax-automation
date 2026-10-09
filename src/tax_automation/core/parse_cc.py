# -*- coding: utf-8 -*-
"""
parse_cc.py
===========
Parses Kotak Mojo RuPay CC statement PDFs (pdfplumber).

Public API
----------
parse_all_statements(cc_dir, fy_start, fy_end)
    -> (cc_df: DataFrame, metas: list[dict])
"""

from __future__ import annotations

import pathlib
import re
import warnings
from datetime import datetime

import pandas as pd
import pdfplumber

from tax_automation.core.cc_category_map import map_category
from tax_automation.config_loader import get_cc_categories_config

_cc_cfg = get_cc_categories_config()

_CC_CATEGORIES = _cc_cfg.get("categories") or [
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
_MERCHANT_OVERRIDES = _cc_cfg.get("merchant_overrides", [])

_TX_RE = re.compile(
    rf"^(\d{{2}}/\d{{2}}/\d{{4}})\s+(.+?)\s+({_CAT_PAT})\s+([\d,]+\.\d{{2}})\s*(Cr)?$",
    re.IGNORECASE,
)

_PMT_RE = re.compile(r"^(\d{2}/\d{2}/\d{4})\s+(DP\w+)\s+([\d,]+\.\d{2})\s+Cr$")

_STMT_DATE_RE = re.compile(r"StatementDate\s+(\d{2}-\w{3}-\d{4})")
_PERIOD_RE = re.compile(r"from\s+(\d{2}-\w{3}-\d{4})\s+to\s+(\d{2}-\w{3}-\d{4})")
_PAY_BY_RE = re.compile(r"Remembertopayby\s+(\d{2}-\w{3}-\d{4})")
_TAD_RE = re.compile(r"TotalAmountDue\(TAD\)\s+Rs\.([\d,]+\.\d{2})")


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
    m = re.match(r"UPI-\d+-(.+)", particulars)
    if m:
        return m.group(1).strip().title()
    return particulars.strip()


def _parse_statement(pdf_path: pathlib.Path) -> tuple[dict | None, pd.DataFrame | None]:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        with pdfplumber.open(pdf_path) as pdf:
            full_text = "\n".join((page.extract_text() or "") for page in pdf.pages)

    period_m = _PERIOD_RE.search(full_text)
    if not period_m:
        return None, None

    period_start = _parse_date(period_m.group(1))
    period_end = _parse_date(period_m.group(2))
    if not period_start or not period_end:
        return None, None

    stmt_date_m = _STMT_DATE_RE.search(full_text)
    pay_by_m = _PAY_BY_RE.search(full_text)
    tad_m = _TAD_RE.search(full_text)

    stmt_date = _parse_date(stmt_date_m.group(1)) if stmt_date_m else None
    pay_by = _parse_date(pay_by_m.group(1)) if pay_by_m else None
    tad = _parse_amount(tad_m.group(1)) if tad_m else 0.0

    meta = {
        "period_start": period_start,
        "period_end": period_end,
        "stmt_date": stmt_date,
        "pay_by": pay_by,
        "tad": tad,
        "pdf_path": str(pdf_path),
    }

    rows: list[dict] = []
    period_label = f"{period_start.strftime('%b-%Y')} to {period_end.strftime('%b-%Y')}"

    for raw_line in full_text.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        m = _TX_RE.match(line)
        if m:
            tx_date = _parse_date(m.group(1))
            particulars = m.group(2).strip()
            cc_cat = m.group(3)
            amount = _parse_amount(m.group(4))
            is_cr = bool(m.group(5))
            merchant = _extract_merchant(particulars)
            narration, acct_head = map_category(cc_cat)

            for override in _MERCHANT_OVERRIDES:
                kw = override.get("merchant_keyword", "")
                if kw and kw.lower() in merchant.lower():
                    amounts = override.get("amounts", [])
                    if amount in amounts:
                        narration = override.get("match_narration", narration)
                        acct_head = override.get("match_account_head", acct_head)
                    else:
                        narration = override.get("default_narration", narration)
                        acct_head = override.get("default_account_head", acct_head)

            rows.append(
                {
                    "TX_Date": tx_date,
                    "Particulars": particulars,
                    "Merchant": merchant,
                    "CC_Category": cc_cat,
                    "Auto_Narration": narration,
                    "Account_Head": acct_head,
                    "DR": 0.0 if is_cr else amount,
                    "CR": amount if is_cr else 0.0,
                    "Statement_Period": period_label,
                    "Pay_By": pay_by,
                    "Source": "CC_TX",
                }
            )
            continue

        if _PMT_RE.match(line):
            continue

    df = pd.DataFrame(rows) if rows else pd.DataFrame()
    return meta, df


def parse_all_statements(
    cc_dir: str | pathlib.Path,
    fy_start: datetime,
    fy_end: datetime,
) -> tuple[pd.DataFrame, list[dict]]:
    cc_dir = pathlib.Path(cc_dir)
    pdfs = sorted(cc_dir.glob("*.pdf"))

    seen: dict[tuple, dict] = {}
    dfs: dict[tuple, pd.DataFrame] = {}

    for pdf_path in pdfs:
        meta, df = _parse_statement(pdf_path)
        if meta is None:
            continue
        key = (meta["period_start"], meta["period_end"])

        if key in seen:
            if meta["stmt_date"] is not None and seen[key]["stmt_date"] is None:
                seen[key] = meta
                dfs[key] = df
        else:
            seen[key] = meta
            dfs[key] = df

    metas: list[dict] = []
    all_dfs: list[pd.DataFrame] = []

    for key, meta in seen.items():
        period_start: datetime = meta["period_start"]
        period_end: datetime = meta["period_end"]

        if period_end < fy_start or period_start > fy_end:
            continue

        df = dfs.get(key, pd.DataFrame())
        if not df.empty:
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
    cache_path = pathlib.Path(cache_path)

    if not cache_path.exists():
        return pd.DataFrame(), []

    try:
        cc_df = pd.read_excel(cache_path, sheet_name="Transactions")
        cc_df["TX_Date"] = pd.to_datetime(cc_df["TX_Date"])
        cc_df["Pay_By"] = pd.to_datetime(cc_df["Pay_By"], errors="coerce")
    except Exception as e:
        warnings.warn(f"Could not load transactions from cache: {e}")
        cc_df = pd.DataFrame()

    try:
        metas_df = pd.read_excel(cache_path, sheet_name="Metadata")
        metas = []
        for _, row in metas_df.iterrows():
            meta = {
                "period_start": (
                    pd.Timestamp(row["Period_Start"]).to_pydatetime()
                    if pd.notna(row["Period_Start"])
                    else None
                ),
                "period_end": (
                    pd.Timestamp(row["Period_End"]).to_pydatetime()
                    if pd.notna(row["Period_End"])
                    else None
                ),
                "stmt_date": (
                    pd.Timestamp(row["Statement_Date"]).to_pydatetime()
                    if pd.notna(row["Statement_Date"])
                    else None
                ),
                "pay_by": (
                    pd.Timestamp(row["Pay_By"]).to_pydatetime()
                    if pd.notna(row["Pay_By"])
                    else None
                ),
                "tad": (
                    float(row["Total_Amount_Due"])
                    if pd.notna(row["Total_Amount_Due"])
                    else 0.0
                ),
                "pdf_path": str(row["PDF_Path"]) if pd.notna(row["PDF_Path"]) else "",
            }
            metas.append(meta)
    except Exception as e:
        warnings.warn(f"Could not load metadata from cache: {e}")
        metas = []

    return cc_df, metas
