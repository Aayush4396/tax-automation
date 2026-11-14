"""Audit source sheets, ledger coverage and unresolved descriptions for one FY."""

from collections import Counter
from html import escape
import json
import re

import pandas as pd

from tax_automation import config_loader as config
from tax_automation.consolidators.generic_consolidator import (
    _excel_source,
    _target_sheet,
    load_file_to_df,
)
from tax_automation.core.auto_header import find_header_row
from tax_automation.core.utils import safe_float
from tax_automation.pipeline.narration import get_col_value, classify_transaction
from tax_automation.rules.loader import build_rule_chain
from tax_automation.tools.reconcile_transfers import read_ledger, _date, fiscal_period
from tax_automation.tools.transfer_matching import account_for_sheet


def _key(tx):
    def normalize(value):
        return re.sub(r"[^A-Z0-9]", "", str(value).upper())

    return (
        tx["date"],
        tx["direction"],
        tx["cents"],
        normalize(tx["particulars"]),
        normalize(
            ""
            if str(tx.get("ref", "")).lower() in ("nan", "none")
            else tx.get("ref", "")
        ).lstrip("0"),
    )


def source_transactions(frame, bank, start, end):
    rows = frame.values.tolist()
    header_index = find_header_row(rows)
    headers = [str(c).strip() for c in rows[header_index]]
    df = pd.DataFrame(rows[header_index + 1 :], columns=headers)
    required = ("col_date", "col_particulars")
    for key in required:
        choices = bank.get(key)
        choices = choices if isinstance(choices, list) else [choices]
        if not any(c in headers for c in choices):
            raise ValueError(f"Missing mapped header: {key}")
    transactions, dated_zero_rows = [], 0
    for _, row in df.iterrows():
        day = _date(get_col_value(row, bank["col_date"]))
        if not day or not start <= day.isoformat() <= end:
            continue
        if bank.get("col_amount") in headers and bank.get("col_direction") in headers:
            positions = [i for i, c in enumerate(headers) if c == bank["col_direction"]]
            direction = (
                str(row.iloc[positions[bank.get("direction_column_occurrence", 0)]])
                .strip()
                .upper()
            )
            amount = safe_float(get_col_value(row, bank["col_amount"]))
            if amount and direction not in ("DR", "CR"):
                raise ValueError("Unknown transaction amount direction")
            debit, credit = (amount, 0) if direction == "DR" else (0, amount)
        else:
            debit = safe_float(get_col_value(row, bank.get("col_dr")))
            credit = safe_float(get_col_value(row, bank.get("col_cr")))
        if not debit and not credit:
            dated_zero_rows += 1
            continue
        if debit and credit:
            raise ValueError("A source transaction contains both debit and credit")
        transactions.append(
            {
                "date": day.isoformat(),
                "direction": "DR" if debit else "CR",
                "cents": round((debit or credit) * 100),
                "particulars": str(get_col_value(row, bank["col_particulars"]) or ""),
                "ref": str(get_col_value(row, bank.get("col_ref")) or ""),
            }
        )
    return transactions, dated_zero_rows


def _open_workbook(path, spec):
    try:
        return _excel_source(path, None)
    except Exception:
        password = config.resolve_password(spec.get("password_env_var"))
        if not password:
            raise ValueError("Workbook unreadable; no usable password configured")
        return _excel_source(path, password)


def audit(fy="FY26"):
    start, end = fiscal_period(fy)
    report = {
        "fy": fy,
        "start": start,
        "end": end,
        "sources": [],
        "coverage": [],
        "issues": [],
        "description_review": [],
    }
    for path in sorted((config.CONFIG_DIR / "entities").glob("*.json")):
        entity = path.stem
        ledger = (
            config.REPO_ROOT / "data" / entity / fy / "output" / "narrated_ledger.xlsx"
        )
        if not ledger.exists():
            continue
        profile = config.get_entity_config(entity)
        registry = config.resolve_entity_bank_registry(entity)
        transactions, issues, coverage = read_ledger(entity, ledger, profile)
        transactions = [t for t in transactions if start <= t["date"] <= end]
        report["issues"].extend(issues)
        try:
            specs = {
                s["filename"]: s
                for s in config.get_consolidation_map(entity, fy).get("files", [])
            }
        except FileNotFoundError:
            specs = {}
        seen_accounts, monetary_accounts, non_monetary_accounts = set(), set(), set()
        aliases = {}
        root = ledger.parent.parent / "input" / "bank_statements"
        for file in sorted(root.iterdir()):
            if file.suffix.lower() not in (".xlsx", ".xls", ".csv", ".pdf"):
                continue
            spec = specs.get(file.name, {})
            try:
                if file.suffix.lower() in (".xlsx", ".xls"):
                    with _open_workbook(file, spec) as xl:
                        frames = [
                            (name, xl.parse(name, header=None))
                            for name in xl.sheet_names
                        ]
                elif file.suffix.lower() == ".csv":
                    frame, _ = load_file_to_df(file)
                    frames = [(None, frame)]
                else:
                    password = config.resolve_password(spec.get("password_env_var"))
                    frame, _ = load_file_to_df(file, password)
                    frames = [(None, frame)]
                for name, frame in frames:
                    entry = {
                        "entity": entity,
                        "file": file.name,
                        "source_sheet": name,
                        "configured": bool(spec),
                        "source_rows": len(frame),
                    }
                    try:
                        if frame.dropna(how="all").empty:
                            entry["status"] = "empty"
                            report["sources"].append(entry)
                            continue
                        target = _target_sheet(name, frame, spec, registry, len(frames))
                        account = account_for_sheet(profile, target)
                        if not account:
                            raise ValueError("Target does not resolve to one account")
                        key = account["account_key"]
                        seen_accounts.add(key)
                        bank = config.get_bank_schema(account["bank"])
                        expected, zero_rows = source_transactions(
                            frame, bank, start, end
                        )
                        if expected:
                            monetary_accounts.add(key)
                        elif zero_rows:
                            non_monetary_accounts.add(key)
                        existing = [t for t in transactions if t["account_key"] == key]
                        left, right = Counter(map(_key, expected)), Counter(
                            map(_key, existing)
                        )
                        missing, extra = left - right, right - left
                        entry.update(
                            account_key=key,
                            target=target,
                            source_transactions=len(expected),
                            ledger_transactions=len(existing),
                            dated_non_monetary_rows=zero_rows,
                            missing_from_ledger=sum(missing.values()),
                            ledger_only_rows=sum(extra.values()),
                            source_debit=sum(
                                t["cents"] for t in expected if t["direction"] == "DR"
                            )
                            / 100,
                            source_credit=sum(
                                t["cents"] for t in expected if t["direction"] == "CR"
                            )
                            / 100,
                            missing_examples=[
                                {"key": list(k), "count": v}
                                for k, v in list(missing.items())[:8]
                            ],
                        )
                        entry["status"] = (
                            "non_monetary_only"
                            if not expected and zero_rows
                            else (
                                "consistent"
                                if not missing and not extra
                                else "source_ledger_difference"
                            )
                        )
                        rows = frame.values.tolist()
                        metadata = " ".join(
                            str(v) for row in rows[: find_header_row(rows)] for v in row
                        )
                        numbers = re.findall(
                            r"Account\s*(?:Number|No)\s*[:.]\s*([0-9]{9,})",
                            metadata,
                            re.I,
                        )
                        alternatives = set()
                        for number in numbers:
                            for other in profile.get("accounts", []):
                                if other.get("bank") != account.get("bank"):
                                    continue
                                suffixes = re.findall(r"\d{3,}", other["account_id"])
                                if any(number.endswith(suffix) for suffix in suffixes):
                                    alternatives.add(other["account_key"])
                        alternatives.discard(key)
                        if len(alternatives) == 1:
                            other_key = next(iter(alternatives))
                            aliases[other_key] = key
                            entry["account_alias_warning"] = {
                                "mapped_account": key,
                                "also_declared_as": other_key,
                                "evidence": "Explicit statement account number suffix",
                            }
                    except Exception as exc:
                        entry.update(status="unresolved_source_sheet", error=str(exc))
                    report["sources"].append(entry)
            except Exception as exc:
                report["sources"].append(
                    {
                        "entity": entity,
                        "file": file.name,
                        "status": "unreadable_source",
                        "error_type": type(exc).__name__,
                        "reason": str(exc),
                    }
                )
        present = {c["account_key"] for c in coverage if c["rows"]}
        for account in profile.get("accounts", []):
            key = account["account_key"]
            report["coverage"].append(
                {
                    "entity": entity,
                    "account_key": key,
                    "status": (
                        "present"
                        if key in present
                        else (
                            "represented_under_other_account_key"
                            if key in aliases
                            else (
                                "source_exists_ledger_missing"
                                if key in monetary_accounts
                                else (
                                    "non_monetary_source_only"
                                    if key in non_monetary_accounts
                                    else (
                                        "source_requires_parser_review"
                                        if key in seen_accounts
                                        else "no_source_found"
                                    )
                                )
                            )
                        )
                    ),
                    "alias_account_key": aliases.get(key),
                }
            )
        chains = {}
        generic = {
            "What is this?",
            "Unclassified - Pending Review",
            "UPI Payment",
            "UPI Receipt",
            "NEFT Transfer",
            "Transfer",
        }
        for tx in transactions:
            if tx["label"] not in generic and "suspense" not in tx["head"].lower():
                continue
            key = tx["account_key"]
            if not key:
                continue
            if key not in chains:
                chains[key] = build_rule_chain(entity, key)
            dr = tx["amount"] if tx["direction"] == "DR" else 0
            cr = tx["amount"] if tx["direction"] == "CR" else 0
            label, head, confidence = classify_transaction(
                tx["particulars"], dr, cr, entity, key, chains[key]
            )
            if label not in generic and "suspense" not in head.lower():
                reason = "current_code_recognizes"
            elif not tx["particulars"].strip():
                reason = "empty_description"
            elif re.search(r"X{3,}|\*{3,}", tx["particulars"], re.I):
                reason = "masked_counterparty"
            else:
                reason = "unresolved_counterparty_or_purpose"
            report["description_review"].append(
                {
                    "transaction": tx,
                    "reason": reason,
                    "current_code_label": label,
                    "current_code_head": head,
                    "current_code_confidence": confidence,
                }
            )
    report["summary"] = {
        "coverage": dict(Counter(c["status"] for c in report["coverage"])),
        "source_statuses": dict(Counter(c["status"] for c in report["sources"])),
        "description_reasons": dict(
            Counter(c["reason"] for c in report["description_review"])
        ),
    }
    return report


def write_report(report, directory):
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "coverage_and_descriptions.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    body = "<h1>Coverage and description audit</h1>"
    body += "<p>" + escape(report["start"] + " through " + report["end"]) + "</p>"
    body += "<p>Duplicate source workbooks are compared separately, never added "
    body += "together. Differences need inspection; they are not automatically "
    body += "missing transactions. Date/reference formatting can also differ.</p>"
    for title, data in [
        ("Summary", report["summary"]),
        ("Account coverage", report["coverage"]),
        ("Source sheet audit", report["sources"]),
        ("Description review", report["description_review"]),
        ("Ledger warnings", report["issues"]),
    ]:
        body += "<details open><summary>" + escape(title) + "</summary><pre>"
        body += escape(json.dumps(data, indent=2)) + "</pre></details>"
    html = (
        '<!doctype html><meta charset="utf-8"><title>Coverage audit</title>'
        "<style>body{font:14px system-ui;margin:24px;color:#183247}"
        "summary{font-weight:bold;padding:12px}pre{white-space:pre-wrap;"
        "background:#f2f6f9;padding:16px}</style>" + body
    )
    path = directory / "coverage_and_descriptions.html"
    path.write_text(html, encoding="utf-8")
    return path


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fy", default="FY26")
    args = parser.parse_args()
    result = audit(args.fy)
    destination = config.REPO_ROOT / "data" / "reconciliation" / args.fy
    print(json.dumps(result["summary"], indent=2))
    print(write_report(result, destination))
