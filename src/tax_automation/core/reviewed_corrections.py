"""Persist and replay explicitly reviewed transaction corrections locally."""

from datetime import date, datetime
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import re

from tax_automation import config_loader as config


def transaction_date(value):
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    text = str(value or "").strip()
    for fmt in (
        "%Y-%m-%d",
        "%Y-%m-%d %H:%M:%S",
        "%d/%m/%Y",
        "%d/%m/%y",
        "%d-%m-%Y",
        "%d-%m-%y",
        "%d %b %Y",
    ):
        try:
            return datetime.strptime(text, fmt).date().isoformat()
        except ValueError:
            pass
    return None


def narration_hash(text):
    normalized = " ".join(str(text or "").upper().split())
    return hashlib.sha256(normalized.encode()).hexdigest()


def correction_path(entity, fy):
    entity, fy = entity.lower(), fy.upper()
    return (
        config.REPO_ROOT / "data" / entity / fy / "output" / "reviewed_corrections.json"
    )


def load_corrections(entity, fy):
    entity, fy = entity.lower(), fy.upper()
    path = correction_path(entity, fy)
    if not path.exists():
        return []
    corrections = json.loads(path.read_text(encoding="utf-8"))
    ids, selectors = set(), set()
    for item in corrections:
        selector = item["selector"]
        if (
            item.get("approved") is not True
            or item["id"] in ids
            or item.get("entity") != entity
            or item.get("fy") != fy
            or not item.get("label")
            or not item.get("head")
            or not 0 <= item.get("confidence", 0.99) <= 1
        ):
            raise ValueError(f"Invalid reviewed correction in {path}")
        required = {
            "account_key",
            "date",
            "direction",
            "cents",
            "reference",
            "narration_sha256",
        }
        if not required <= selector.keys() or selector["direction"] not in ("DR", "CR"):
            raise ValueError(f"Incomplete correction selector in {path}")
        if not selector["reference"] or len(selector["narration_sha256"]) != 64:
            raise ValueError(f"Unsafe correction selector in {path}")
        signature = json.dumps(selector, sort_keys=True)
        if signature in selectors:
            raise ValueError(f"Duplicate correction selector in {path}")
        selectors.add(signature)
        ids.add(item["id"])
    return corrections


def matches(record, selector):
    debit = int((Decimal(str(record.get("DR") or 0)) * 100).quantize(Decimal("1")))
    credit = int((Decimal(str(record.get("CR") or 0)) * 100).quantize(Decimal("1")))
    ref = str(record.get("Ref") or "").upper().lstrip("0")
    expected = selector["reference"].upper().lstrip("0")
    description = str(record.get("Particulars") or "")
    reference_matches = ref == expected or bool(
        re.search(
            r"(?<![A-Z0-9])" + re.escape(expected) + r"(?![A-Z0-9])", description, re.I
        )
    )
    return (
        record.get("Bank_Key") == selector["account_key"]
        and transaction_date(record.get("TX_Date")) == selector["date"]
        and (debit if selector["direction"] == "DR" else credit) == selector["cents"]
        and not (credit if selector["direction"] == "DR" else debit)
        and reference_matches
        and narration_hash(description) == selector["narration_sha256"]
    )


def apply_corrections(records, corrections):
    audit, touched = [], set()
    for item in corrections:
        if item.get("approved") is not True:
            raise ValueError("Only explicitly approved corrections can be applied")
        selected = [r for r in records if matches(r, item["selector"])]
        if len(selected) > 1:
            raise ValueError(f"Correction {item['id']} matches duplicate transactions")
        if not selected:
            continue
        record = selected[0]
        if id(record) in touched:
            raise ValueError("More than one correction targets the same transaction")
        touched.add(id(record))
        audit.append(
            {
                "id": item["id"],
                "before_label": record["Auto_Narration"],
                "before_head": record["Account_Head"],
                "label": item["label"],
                "head": item["head"],
                "selector": item["selector"],
            }
        )
        record.update(
            Auto_Narration=item["label"],
            Account_Head=item["head"],
            Confidence=item.get("confidence", 0.99),
        )
    return audit


def update_existing_ledger(path: Path, entity, fy):
    """Patch all transaction copies; preserve formulas and human review notes."""
    from openpyxl import load_workbook
    from openpyxl.workbook.properties import CalcProperties
    from openpyxl.styles import PatternFill
    from tax_automation.tools.transfer_matching import account_for_sheet
    from tax_automation.exporters.exporter import get_pivot_category_for_row

    corrections = load_corrections(entity, fy)
    profile = config.get_entity_config(entity)
    workbook = load_workbook(path)
    audit, bank_matches = [], []
    aliases = {
        "TX_Date": ("tx date", "date"),
        "DR": ("dr",),
        "CR": ("cr",),
        "Particulars": ("particulars",),
        "Ref": ("ref",),
        "Auto_Narration": ("auto_narration", "narration"),
        "Account_Head": ("account_head", "account head"),
        "Confidence": ("confidence",),
        "Account_ID": ("account no", "account_id"),
        "Pivot_Category": ("pivot category", "pivot_category"),
    }
    try:
        for ws in workbook:
            header = None
            for row in ws.iter_rows(max_row=min(ws.max_row, 40)):
                keys = {str(c.value or "").strip().lower(): c.column for c in row}
                if {"particulars", "dr", "cr"} <= keys.keys():
                    header = {
                        k: next((keys[a] for a in names if a in keys), None)
                        for k, names in aliases.items()
                    }
                    start_row = row[0].row + 1
                    break
            if header is None:
                continue
            bound = account_for_sheet(profile, ws.title)
            for cells in ws.iter_rows(min_row=start_row):
                record = {k: cells[col - 1].value for k, col in header.items() if col}
                if transaction_date(record.get("TX_Date")) is None:
                    continue
                account = bound
                if not account:
                    accounts = [
                        a
                        for a in profile.get("accounts", [])
                        if a["account_id"] == record.get("Account_ID")
                    ]
                    account = accounts[0] if len(accounts) == 1 else None
                if not account:
                    continue
                record["Bank_Key"] = account["account_key"]
                for item in corrections:
                    if not matches(record, item["selector"]):
                        continue
                    changes = {
                        "Auto_Narration": item["label"],
                        "Account_Head": item["head"],
                        "Confidence": item.get("confidence", 0.99),
                    }
                    changes["Pivot_Category"] = get_pivot_category_for_row(
                        record.get("DR", 0),
                        record.get("CR", 0),
                        item["head"],
                        item["label"],
                        profile.get("pivot_overrides"),
                    )
                    before = {}
                    for key, value in changes.items():
                        if header.get(key):
                            cell = cells[header[key] - 1]
                            before[key] = cell.value
                            cell.value = value
                            if key == "Confidence":
                                cell.fill = PatternFill("solid", fgColor="C6EFCE")
                    audit.append(
                        {
                            "id": item["id"],
                            "sheet": ws.title,
                            "row": cells[0].row,
                            "before": before,
                            "after": {
                                k: v for k, v in changes.items() if header.get(k)
                            },
                        }
                    )
                    if bound:
                        bank_matches.append(item["id"])
        for item in corrections:
            if bank_matches.count(item["id"]) != 1:
                raise ValueError(f"Correction {item['id']} must match one bank row")
        workbook.calculation = CalcProperties(fullCalcOnLoad=True, forceFullCalc=True)
        temporary = path.with_name(path.stem + ".correcting.xlsx")
        workbook.save(temporary)
        temporary.replace(path)
    finally:
        workbook.close()
    (path.parent / "correction_application_audit.json").write_text(
        json.dumps(audit, indent=2, default=str), encoding="utf-8"
    )
    return audit
