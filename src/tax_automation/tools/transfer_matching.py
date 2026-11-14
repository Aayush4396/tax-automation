"""Evidence-based transfer matching without editing source classifications."""

from collections import defaultdict
import re

from tax_automation import config_loader as config


def settings():
    path = config.CONFIG_DIR / "reconciliation.json"
    value = config.read_config(path)
    re.compile(value["transfer_pattern"], re.I)
    for pattern in value["non_transfer_patterns"]:
        re.compile(pattern, re.I)
    for pattern in value["purpose_patterns"].values():
        re.compile(pattern, re.I)
    for entry in value.get("counterparty_bank_patterns", []):
        compiled = re.compile(entry["pattern"], re.I)
        if compiled.groups != 1:
            raise ValueError("Counterparty bank patterns require one prefix group")
    for pattern in value["narration_reference_patterns"]:
        re.compile(pattern, re.I)
    return value


def account_for_sheet(profile, sheet):
    """Exact configured names/aliases, then a unique bare bank name (legacy tabs)."""
    accounts = profile.get("accounts", [])
    matches = [
        a
        for a in accounts
        if sheet.casefold()
        in {str(v).casefold() for v in [a["sheet_name"], *a.get("sheet_aliases", [])]}
    ]
    if not matches:
        matches = [
            a for a in accounts if sheet.casefold() == a.get("bank", "").casefold()
        ]
    return matches[0] if len(matches) == 1 else None


def references(tx, options):
    refs = set()
    raw = str(tx.get("ref") or "").strip().upper()
    if re.fullmatch(r"[A-Z0-9]{8,}", raw) and len(set(raw)) > 1:
        refs.add(raw.lstrip("0"))
    for pattern in options["narration_reference_patterns"]:
        for match in re.finditer(pattern, tx["particulars"].upper()):
            token = match.group(0)
            if len(set(token)) > 1:
                refs.add(token.lstrip("0"))
    # Account numbers are identities, not payment references.
    return refs


def account_mentions(tx, profiles):
    """Full configured numbers/VPAs only: suffixes never identify an owner."""
    mentions = set()
    text = re.sub(r"\s+", "", tx["particulars"])
    for eid, profile in profiles.items():
        for account in profile.get("accounts", []):
            number = account.get("account_number", "")
            if re.fullmatch(r"\d{9,}", number) and re.search(
                r"(?<![\dXx*])" + re.escape(number) + r"(?!\d)", text
            ):
                mentions.add((eid, account["account_key"]))
            for vpa in account.get("vpas", []):
                if re.search(
                    r"(?<![\w.@-])" + re.escape(vpa) + r"(?![\w.@-])",
                    tx["particulars"],
                    re.I,
                ):
                    mentions.add((eid, account["account_key"]))
    return mentions


def self_identity(tx, profile):
    return any(
        re.search(p, tx["particulars"], re.I) for p in profile.get("self_patterns", [])
    )


def _correction(tx, target, profiles, link_member):
    members = [
        m
        for m in profiles[tx["entity"]].get("family_members", [])
        if link_member(m, profiles) == target
    ]
    name = profiles[target]["display_name"]
    head = name
    if len(members) == 1:
        name = members[0]["name"]
        head = members[0].get("account_head", name)
    return {
        "source_row": tx["id"],
        "previous_label": tx["label"],
        "previous_head": tx["head"],
        "proposed_label": f"Transfer - {name}",
        "proposed_head": head,
        "counterparty_entity": target,
        "applied": False,
    }


def match(
    transactions,
    profiles,
    days,
    targets,
    parse_date,
    link_member,
    coverage=None,
    options=None,
):
    if not 0 <= days <= 30:
        raise ValueError("Date window must be between 0 and 30 days")
    options = options if options is not None else settings()
    lookup = {t["id"]: t for t in transactions}
    if len(lookup) != len(transactions):
        raise ValueError("Transaction row identifiers must be unique")
    raw, claims, refs, accounts = {}, {}, {}, {}
    self_named, excluded, purposes = {}, {}, {}
    account_index = {
        (eid, a["account_key"]): a
        for eid, profile in profiles.items()
        for a in profile.get("accounts", [])
    }
    bank_prefixes = {}
    for account in account_index.values():
        bank = account.get("bank", "")
        path = config.CONFIG_DIR / "banks" / f"{bank}.json"
        if bank not in bank_prefixes:
            bank_prefixes[bank] = (
                set(config.read_config(path).get("ifsc_prefixes", []))
                if path.exists()
                else set()
            )
    counterparty_banks = {}
    buckets = defaultdict(list)
    for tx in transactions:
        key = tx["id"]
        raw[key] = targets(tx, profiles)
        claims[key] = targets(tx, profiles, classification=True)
        accounts[key] = account_mentions(tx, profiles)
        refs[key] = references(tx, options)
        counterparty_banks[key] = {
            m.group(1).upper()
            for entry in options.get("counterparty_bank_patterns", [])
            if entry["direction"] == tx["direction"]
            for m in re.finditer(entry["pattern"], tx["particulars"], re.I)
        }
        # Avoid treating any configured full account identifier as a UTR/RRN.
        for profile in profiles.values():
            for account in profile.get("accounts", []):
                refs[key].discard(account.get("account_number", "").lstrip("0"))
        self_named[key] = self_identity(tx, profiles[tx["entity"]]) and bool(
            re.search(options["transfer_pattern"], tx["particulars"], re.I)
        )
        excluded[key] = any(
            re.search(p, tx["particulars"], re.I)
            for p in options["non_transfer_patterns"]
        )
        purposes[key] = {
            name
            for name, pattern in options["purpose_patterns"].items()
            if re.search(pattern, tx["particulars"], re.I)
        }
        buckets[tx["cents"]].append(tx)

    edges, rejected = {}, defaultdict(list)
    for debit in transactions:
        if debit["direction"] != "DR":
            continue
        for credit in buckets[debit["cents"]]:
            if credit["direction"] != "CR":
                continue
            a, b = debit["id"], credit["id"]
            same = debit["entity"] == credit["entity"]
            same_account = debit.get("account_key") and debit.get(
                "account_key"
            ) == credit.get("account_key")
            if same and (same_account or debit.get("sheet") == credit.get("sheet")):
                continue
            gap = abs((parse_date(debit["date"]) - parse_date(credit["date"])).days)
            if gap > days:
                continue
            shared = refs[a] & refs[b]
            identities = (credit["entity"] in raw[a], debit["entity"] in raw[b])
            destination = (credit["entity"], credit.get("account_key")) in accounts[a]
            origin = (debit["entity"], debit.get("account_key")) in accounts[b]
            self_evidence = same and (self_named[a] or self_named[b])
            if not (any(identities) or destination or origin or self_evidence):
                continue
            reason = None
            for x, y in ((a, credit), (b, debit)):
                # A positive counterparty identity must not contradict the pair.
                if "__external__" in raw[x] or (
                    raw[x] and y["entity"] not in raw[x] and not same
                ):
                    reason = "counterparty_identity_conflict"
                other_account = account_index.get(
                    (y["entity"], y.get("account_key")), {}
                )
                expected_prefixes = bank_prefixes.get(other_account.get("bank"), set())
                if (
                    counterparty_banks[x]
                    and expected_prefixes
                    and not counterparty_banks[x] & expected_prefixes
                ):
                    reason = "counterparty_bank_conflict"
                foreign = {owner for owner, _ in accounts[x]}
                if foreign and y["entity"] not in foreign:
                    reason = "counterparty_account_conflict"
                target_keys = {
                    key for owner, key in accounts[x] if owner == y["entity"]
                }
                if (
                    target_keys
                    and y.get("account_key")
                    and y["account_key"] not in target_keys
                ):
                    reason = "counterparty_account_conflict"
            if (
                not same
                and ((self_named[a] and not raw[a]) or (self_named[b] and not raw[b]))
                and not (shared or destination or origin)
            ):
                reason = "self_transfer_evidence"
            if same and not (shared or destination or origin):
                reason = "insufficient_self_transfer_evidence"
            if excluded[a] or excluded[b]:
                reason = "non_transfer_description"
            for p, q in options["incompatible_purposes"]:
                if (p in purposes[a] and q in purposes[b]) or (
                    q in purposes[a] and p in purposes[b]
                ):
                    reason = "incompatible_transfer_purposes"
            if refs[a] and refs[b] and not shared:
                reason = "conflicting_payment_references"
            if reason:
                for x, y in ((a, b), (b, a)):
                    rejected[x].append({"candidate": y, "reason": reason})
                continue
            strength = 3 if shared else 2 if destination or origin else 1
            edges[frozenset((a, b))] = {
                "a": a,
                "b": b,
                "scope": "self" if same else "inter_entity",
                "strength": strength,
                "date_gap_days": gap,
                "identity_sides": sum(identities),
                "shared_references": sorted(shared),
                "full_account_or_vpa_evidence": destination or origin,
                "certainty": "strong" if strength >= 2 else "provisional",
            }

    # Lock only reciprocal unique best edges at each evidence tier. Ties remain
    # unresolved; lower evidence must never settle a higher-tier conflict.
    used, blocked, results = set(), set(), []
    for tier in (3, 2, 1):
        available = [
            e
            for e in edges.values()
            if e["strength"] == tier and not ({e["a"], e["b"]} & (used | blocked))
        ]
        adjacent = defaultdict(list)
        for edge in available:
            adjacent[edge["a"]].append(edge)
            adjacent[edge["b"]].append(edge)
        for edge in available:
            a, b = edge["a"], edge["b"]
            if len(adjacent[a]) != 1 or len(adjacent[b]) != 1:
                continue
            if {a, b} & used:
                continue
            left, right = lookup[a], lookup[b]
            used.update((a, b))
            if edge["scope"] == "self":
                agrees = all(t["label"].startswith("Contra -") for t in (left, right))
            else:
                agrees = claims[a] == {right["entity"]} and claims[b] == {
                    left["entity"]
                }
            suggestions = []
            if edge["scope"] == "self":
                for tx, other in ((left, right), (right, left)):
                    target_account = account_index.get(
                        (other["entity"], other.get("account_key"))
                    )
                    if not target_account:
                        continue
                    expected_head = target_account["account_id"]
                    if (
                        not tx["label"].startswith("Contra -")
                        or tx["head"] != expected_head
                    ):
                        agrees = False
                        suggestions.append(
                            {
                                "source_row": tx["id"],
                                "previous_label": tx["label"],
                                "previous_head": tx["head"],
                                "proposed_label": "Contra - "
                                + target_account.get(
                                    "display_name", target_account["account_id"]
                                ),
                                "proposed_head": expected_head,
                                "counterpart_row": other["id"],
                                "evidence": edge,
                                "applied": False,
                            }
                        )
            if edge["scope"] == "inter_entity":
                for tx, other in ((left, right), (right, left)):
                    if claims[tx["id"]] != {other["entity"]}:
                        suggestion = _correction(
                            tx, other["entity"], profiles, link_member
                        )
                        suggestion.update(counterpart_row=other["id"], evidence=edge)
                        suggestions.append(suggestion)
            results.append(
                {
                    "status": (
                        "matched_classification_agrees"
                        if agrees
                        else "matched_review_classification"
                    ),
                    "scope": edge["scope"],
                    "left": left,
                    "right": right,
                    "evidence": edge,
                    "proposed_corrections": suggestions,
                }
            )
        blocked.update(k for k in adjacent if k not in used)

    for tx in transactions:
        a = tx["id"]
        if a in used:
            continue
        candidates = []
        for edge in edges.values():
            if a not in (edge["a"], edge["b"]):
                continue
            b = edge["b"] if a == edge["a"] else edge["a"]
            if b in used:
                rejected[a].append(
                    {"candidate": b, "reason": "counterpart_matched_elsewhere"}
                )
            else:
                candidates.append(b)
        target_entities = (raw[a] | claims[a]) & profiles.keys()
        account_targets = {eid for eid, _ in accounts[a]} - {tx["entity"]}
        target_entities |= account_targets
        self_transfer = (
            not target_entities
            and not excluded[a]
            and (self_named[a] or tx["label"].startswith("Contra -"))
        )
        if candidates:
            status = "multiple_plausible_counterparts"
            explanation = "More than one viable pairing remains in the evidence graph."
        elif target_entities:
            status, explanation = _coverage_status(
                tx, target_entities, accounts[a], profiles, coverage or []
            )
        elif self_transfer:
            status = "self_transfer_no_counterpart"
            explanation = "Own identity appears; no supported opposite account entry."
        elif rejected[a]:
            status = "rejected_weaker_candidates"
            explanation = "Lookalikes rejected; not a confirmed inter-entity transfer."
        else:
            continue
        results.append(
            {
                "status": status,
                "scope": (
                    "self"
                    if self_transfer
                    else "inter_entity" if target_entities else "unconfirmed"
                ),
                "left": tx,
                "right": None,
                "candidates": sorted(candidates),
                "reason": explanation,
                "rejected_candidates": rejected[a],
                "raw_targets": sorted(raw[a]),
                "classified_targets": sorted(claims[a]),
            }
        )
    return results


def _coverage_status(tx, targets, account_targets, profiles, coverage):
    for eid in sorted(targets):
        available = [c for c in coverage if c["entity"] == eid]
        expected = {a["account_key"] for a in profiles[eid].get("accounts", [])}
        present = {c.get("account_key") for c in available}
        known = {key for owner, key in account_targets if owner == eid}
        if known - present:
            return (
                "counterparty_account_unavailable",
                f"{eid}: identified account absent from usable ledger coverage.",
            )
        if expected - present:
            return (
                "counterparty_coverage_incomplete",
                f"{eid}: configured accounts absent; counterpart not found.",
            )
        if available and not any(
            c.get("first_date") and c["first_date"] <= tx["date"] <= c["last_date"]
            for c in available
        ):
            return (
                "counterparty_coverage_incomplete",
                f"{eid}: transaction date outside available statement coverage.",
            )
    return (
        "no_matching_entry",
        "No eligible opposite entry; review description, references and coverage.",
    )
