"""Read-only, one-to-one reconciliation across entity ledgers.

Run: python -m tax_automation.tools.reconcile_transfers --fy FY26
"""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from html import escape
import json
from pathlib import Path
import re

from openpyxl import load_workbook

from tax_automation import config_loader as config


def _date(value):
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value or "").strip()
    for fmt in (
        "%d/%m/%y",
        "%d/%m/%Y",
        "%d-%m-%Y",
        "%d-%m-%y",
        "%Y-%m-%d",
        "%Y-%m-%d %H:%M:%S",
        "%d %b %Y",
    ):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            pass
    return None


def _cents(value):
    if value in (None, "", "-"):
        return 0
    try:
        number = Decimal(str(value).replace(",", "").strip())
        if not number.is_finite() or number < 0:
            raise ValueError("Amount must be finite and nonnegative")
        return int((number * 100).quantize(Decimal("1")))
    except InvalidOperation as exc:
        raise ValueError(f"Invalid amount: {value!r}") from exc


def _norm(value):
    return re.sub(r"[^a-z0-9]", "", str(value).lower())


def _linked_member(member, profiles):
    explicit = member.get("entity_id")
    if explicit:
        return explicit if explicit in profiles else None
    name = member.get("name", "")

    def compatible(alias):
        left = re.findall(r"[A-Z]+", name.upper())
        right = re.findall(r"[A-Z]+", alias.upper())
        return (
            len(left) >= 2
            and len(right) >= 2
            and (left[0], left[-1]) == (right[0], right[-1])
        )

    hits = [
        eid
        for eid, profile in profiles.items()
        if any(
            _norm(name) == _norm(alias) or compatible(alias)
            for alias in [profile["display_name"], *profile.get("identity_aliases", [])]
        )
        or any(re.fullmatch(p, name, re.I) for p in profile.get("self_patterns", []))
    ]
    return hits[0] if len(hits) == 1 else None


def _targets(tx, profiles, classification=False):
    source = profiles[tx["entity"]]
    text = tx["particulars"]
    members = source.get("family_members", [])
    if classification:
        names = {tx["head"].strip().casefold()}
        label = tx["label"]
        if label.startswith("Transfer - "):
            names.add(label[len("Transfer - ") :].strip().casefold())
        return {
            eid
            for member in members
            if {
                member.get("name", "").casefold(),
                member.get("account_head", "").casefold(),
            }
            & names
            for eid in [_linked_member(member, profiles)]
            if eid and eid != tx["entity"]
        }
    # Specific unavailable relatives (e.g. HUF) must not become the individual.
    external = [m for m in members if not _linked_member(m, profiles)]
    if any(re.search(p, text, re.I) for m in external for p in m.get("patterns", [])):
        return {"__external__"}
    from tax_automation.core.person_identity import identity_matches

    identities = {}
    for eid, profile in profiles.items():
        identities[eid] = {
            "names": [profile["display_name"], *profile.get("identity_aliases", [])],
            "patterns": list(profile.get("self_patterns", [])),
            "literals": list(profile.get("self_vpas", [])),
        }
    for member in members:
        eid = _linked_member(member, profiles)
        if eid:
            identities[eid]["names"] += [member["name"]]
            identities[eid]["names"] += member.get("identity_aliases", [])
            identities[eid]["patterns"] += member.get("patterns", [])
    # Include self when comparing spans, then remove it from counterparties.
    return identity_matches(text, identities) - {tx["entity"]}


def read_ledger(entity, path, profile):
    from tax_automation.tools.transfer_matching import account_for_sheet

    transactions, issues, coverage = [], [], []
    excluded = set(profile.get("output_sheet_names", [])) | {
        "For Tally",
        "Conso",
        "Tally Vouchers",
        "Combined Bank Book",
        "Bank Summary",
        "Monthly Pivot",
        "Monthly Cash Flow Pivot",
        "Colour Legend",
        "Classification Legend",
        "Credit Card Book",
        "Guidelines",
    }
    wb = load_workbook(path, read_only=True, data_only=True)
    try:
        for ws in wb:
            if ws.title in excluded:
                continue
            account = account_for_sheet(profile, ws.title)
            account_key = account["account_key"] if account else None
            rows = ws.iter_rows(values_only=True)
            header = None
            for row_number, row in enumerate(rows, 1):
                keys = [str(v or "").strip().lower() for v in row]
                if {"particulars", "dr", "cr", "auto_narration"} <= set(keys):
                    header = {k: i for i, k in enumerate(keys)}
                    break
                if row_number >= 40:
                    break
            if header is None:
                issues.append(f"{entity}/{ws.title}: no supported ledger header")
                continue
            count = 0
            for row_number, row in enumerate(rows, row_number + 1):

                def value(key):
                    idx = header.get(key)
                    return row[idx] if idx is not None and idx < len(row) else None

                try:
                    debit, credit = _cents(value("dr")), _cents(value("cr"))
                except ValueError as exc:
                    issues.append(f"{entity}/{ws.title}:{row_number}: {exc}")
                    continue
                if not debit and not credit:
                    continue
                day = _date(value("date") or value("tx_date"))
                if not day or (debit and credit):
                    issues.append(
                        f"{entity}/{ws.title}:{row_number}: invalid date/direction"
                    )
                    continue
                transactions.append(
                    {
                        "id": f"{entity}/{ws.title}:{row_number}",
                        "entity": entity,
                        "file": str(path.resolve()),
                        "sheet": ws.title,
                        "row": row_number,
                        "account_key": account_key,
                        "date": day.isoformat(),
                        "direction": "DR" if debit else "CR",
                        "cents": debit or credit,
                        "amount": (debit or credit) / 100,
                        "particulars": str(value("particulars") or ""),
                        "ref": str(value("ref") or ""),
                        "label": str(value("auto_narration") or ""),
                        "head": str(value("account_head") or ""),
                    }
                )
                count += 1
            sheet_dates = [tx["date"] for tx in transactions if tx["sheet"] == ws.title]
            coverage.append(
                {
                    "entity": entity,
                    "sheet": ws.title,
                    "rows": count,
                    "account_key": account_key,
                    "first_date": min(sheet_dates, default=None),
                    "last_date": max(sheet_dates, default=None),
                }
            )
    finally:
        wb.close()
    present = {c["account_key"] for c in coverage}
    configured = {a["account_key"] for a in profile.get("accounts", [])}
    missing = sorted(configured - present)
    if missing:
        issues.append(
            f"{entity}: configured accounts absent from ledger coverage: "
            + ", ".join(missing)
        )
    if not transactions:
        issues.append(f"{entity}: no usable transactions")
    return transactions, issues, coverage


def match_transfers(transactions, profiles, days=3, coverage=None, options=None):
    from tax_automation.tools.transfer_matching import match

    return match(
        transactions,
        profiles,
        days,
        _targets,
        _date,
        _linked_member,
        coverage=coverage,
        options=options,
    )


def fiscal_period(fy):
    if not re.fullmatch(r"FY(?:[0-9]{2}|[0-9]{4})", fy):
        raise ValueError("Use a financial year such as FY26 or FY2026")
    year = int(fy[2:])
    if len(fy) == 4:
        year += 2000
    if not 1901 <= year <= 9999:
        raise ValueError("Financial year is outside the supported range")
    return date(year - 1, 4, 1).isoformat(), date(year, 3, 31).isoformat()


def reconcile(fy, entity_ids=None, days=3):
    start, end = fiscal_period(fy)
    year = int(end[:4])
    fy = f"FY{year % 100:02d}"
    if not 0 <= days <= 30:
        raise ValueError("Date window must be between 0 and 30 days")
    ids = entity_ids or sorted(
        p.stem for p in (config.CONFIG_DIR / "entities").glob("*.json")
    )
    profiles = {eid: config.get_entity_config(eid) for eid in ids}
    transactions, issues, coverage, sources = [], [], [], []
    excluded_outside_period = 0
    for eid, profile in profiles.items():
        path = config.REPO_ROOT / "data" / eid / fy / "output" / "narrated_ledger.xlsx"
        if not path.exists():
            issues.append(f"{eid}: ledger unavailable for {fy}")
            continue
        rows, errors, sheets = read_ledger(eid, path, profile)
        selected = [t for t in rows if start <= t["date"] <= end]
        excluded_outside_period += len(rows) - len(selected)
        for sheet in sheets:
            dates = [t["date"] for t in selected if t["sheet"] == sheet["sheet"]]
            sheet.update(
                rows=len(dates),
                first_date=min(dates, default=None),
                last_date=max(dates, default=None),
            )
        transactions.extend(selected)
        issues.extend(errors)
        coverage.extend(sheets)
        sources.append(
            {
                "entity": eid,
                "path": str(path.resolve()),
                "modified": datetime.fromtimestamp(path.stat().st_mtime).isoformat(),
            }
        )
    if len(sources) < 2:
        raise ValueError("At least two available entity ledgers are required")
    from tax_automation.tools.transfer_matching import settings

    policy = settings()
    results = match_transfers(
        transactions, profiles, days, coverage=coverage, options=policy
    )
    return {
        "fy": fy,
        "date_window_days": days,
        "sources": sources,
        "period_start": start,
        "period_end": end,
        "excluded_outside_period": excluded_outside_period,
        "matching_policy": policy,
        "transactions_scanned": len(transactions),
        "coverage": coverage,
        "issues": issues,
        "counts": dict(Counter(r["status"] for r in results)),
        "scope_counts": {
            scope: dict(Counter(r["status"] for r in results if r["scope"] == scope))
            for scope in ("inter_entity", "self", "unconfirmed")
        },
        "proposed_corrections": [
            c for r in results for c in r.get("proposed_corrections", [])
        ],
        "results": results,
    }


def write_report(report, directory):
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "transfer_reconciliation.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    rows = []
    for result in report["results"]:
        cells = [result["status"], result.get("scope", "")]
        for side in ("left", "right"):
            tx = result.get(side) or {}
            cells += [
                tx.get(k, "")
                for k in (
                    "id",
                    "date",
                    "direction",
                    "amount",
                    "particulars",
                    "label",
                    "head",
                )
            ]
        detail = {
            k: result[k]
            for k in (
                "reason",
                "evidence",
                "candidates",
                "rejected_candidates",
                "proposed_corrections",
            )
            if k in result
        }
        cells.append(json.dumps(detail))
        cells_html = "".join(f"<td>{escape(str(c))}</td>" for c in cells)
        rows.append("<tr>" + cells_html + "</tr>")
    titles = ["Status", "Scope"]
    for side in ("Source", "Counterpart"):
        titles += [
            f"{side} {k}"
            for k in (
                "row",
                "date",
                "direction",
                "amount",
                "narration",
                "label",
                "head",
            )
        ]
    titles += ["Matching evidence / candidate row IDs"]
    html = """<!doctype html><meta charset="utf-8">
<title>Transfer reconciliation</title>
<style>body{font:14px system-ui;margin:28px;color:#173047}
table{border-collapse:collapse}
th,td{padding:10px;border:1px solid #ccd6df;min-width:100px;vertical-align:top}
th{background:#173047;color:white;position:sticky;top:0}input{padding:10px;width:450px}
tr:nth-child(even){background:#f0f5f8}</style><h1>Entity transfer reconciliation</h1>"""
    html += f'<p>{escape(report["fy"])} | '
    html += f'{report["transactions_scanned"]} transactions scanned'
    html += f' | exact amount | +/-{report["date_window_days"]} days</p>'
    html += "<pre>" + escape(json.dumps(report["scope_counts"], indent=2))
    html += "</pre>"
    html += "<p>Proposed matches are review evidence, not proof of tax treatment. "
    html += "No source classifications were changed. Missing counterparts can reflect "
    html += "incomplete statement coverage. Each row is used in at most "
    html += "one matched pair.</p>"
    html += "<details><summary>Source files and coverage warnings</summary><pre>"
    metadata = {
        k: report[k] for k in ("sources", "coverage", "issues", "matching_policy")
    }
    html += escape(json.dumps(metadata, indent=2))
    html += '</pre></details><p><input id="filter" '
    html += 'placeholder="Filter status, entity, narration or amount"></p>'
    html += "<table><thead><tr>" + "".join(f"<th>{escape(t)}</th>" for t in titles)
    html += "</tr></thead><tbody>" + "".join(rows) + "</tbody></table>"
    html += """<script>document.getElementById('filter').oninput=function(){
for(const row of document.querySelectorAll('tbody tr'))
row.hidden=!row.textContent.toLowerCase().includes(this.value.toLowerCase());
};</script>"""
    path = directory / "transfer_reconciliation.html"
    path.write_text(html, encoding="utf-8")
    return path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fy", required=True)
    parser.add_argument("--entities", nargs="+")
    parser.add_argument("--days", type=int, default=3)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--person-to-person", action="store_true")
    args = parser.parse_args()
    report = reconcile(args.fy.upper(), args.entities, args.days)
    if args.person_to_person:
        report["results"] = [
            r for r in report["results"] if r["scope"] == "inter_entity"
        ]
        report["counts"] = dict(Counter(r["status"] for r in report["results"]))
        report["scope_counts"] = {"inter_entity": report["counts"]}
        report["proposed_corrections"] = [
            c for r in report["results"] for c in r.get("proposed_corrections", [])
        ]
    directory = args.output or (
        config.REPO_ROOT / "data" / "reconciliation" / args.fy.upper()
    )
    path = write_report(report, directory)
    summary = {
        k: report[k]
        for k in ("counts", "scope_counts", "transactions_scanned", "issues")
    }
    print(json.dumps(summary, indent=2))
    print(path)


if __name__ == "__main__":
    main()
