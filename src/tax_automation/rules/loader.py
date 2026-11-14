# -*- coding: utf-8 -*-
"""loader.py.

Dynamic rule chain compiler:
Assembles runtime classification rules combining:
1. Dynamic Entity Custom Rules (layer "entity": exact amounts, specific overrides)
2. Dynamic Rent Rules (synthesized from entity_config["rent"])
3. Dynamic Contra Rules (synthesized from entity_config["accounts"] + self identity)
4. Dynamic Family Transfer Rules (synthesized from entity_config["family_members"])
5. Bank Base Rules (loaded directly from config/banks/<bank>.json rules_module)
6. Entity Custom Rules (layer "common": evaluated just before universal rules)
7. Agnostic Common Rules (from config/rules_common.json)
"""

from __future__ import annotations
import importlib
import re
from typing import Any

from tax_automation.config_loader import (
    get_bank_schema,
    get_entity_config,
    get_declarative_common_rules,
)
from tax_automation.rules.common_base import (
    _compile_declarative_rule,
)


def _get_bank_alias_tokens(bank_key: str) -> list[str]:
    """Returns alias token regex patterns for a bank from its schema JSON.

    Each bank config file declares an ``alias_tokens`` array.  This replaces
    the former hard-coded ``_BANK_ALIAS_TOKENS`` dict so that adding a new bank
    never requires a Python code change — only a config file update.
    """
    try:
        schema = get_bank_schema(bank_key)
        tokens = schema.get("alias_tokens")
        if tokens and isinstance(tokens, list):
            return tokens
    except Exception:
        pass
    # Graceful fallback: match the bare bank key (better than nothing)
    return [re.escape(bank_key)]


def load_bank_rules(bank_key: str, rules_module: str | None = None) -> list[tuple]:
    """Loads bank base classification rules from JSON config or Python module.

    Priority:
    1. Declarative ``"rules"`` array in ``config/banks/<bank>.json`` (compiled
       via ``_compile_declarative_rule``).
    2. Optional Python module specified by ``rules_module`` (or fallback
       ``tax_automation.rules.banks.<bank>`` only if ``"rules"`` is not present
       in the JSON schema).
    """
    key = bank_key.lower()

    schema = get_bank_schema(key)
    rules: list[tuple] = []

    # 1. Load declarative rules from bank JSON schema
    declarative_rules = schema.get("rules")
    has_declarative_key = "rules" in schema and isinstance(declarative_rules, list)
    if has_declarative_key:
        for r_dict in declarative_rules:
            try:
                rules.append(_compile_declarative_rule(r_dict))
            except Exception as exc:
                raise ValueError(f"Invalid rule in bank {key}: {r_dict}") from exc

    # 2. Load optional Python module rules if configured or no declarative key
    module_name = rules_module or schema.get("rules_module")
    if not module_name and not has_declarative_key:
        module_name = f"tax_automation.rules.banks.{key}"

    if module_name:
        try:
            mod = importlib.import_module(module_name)
            for var_name in dir(mod):
                if var_name.startswith("RULES_") and isinstance(
                    getattr(mod, var_name), list
                ):
                    rules.extend(getattr(mod, var_name))
                    break
        except (ImportError, AttributeError):
            pass

    return rules


def build_dynamic_contra_rules(
    entity_config: dict[str, Any], current_account_key: str
) -> list[tuple]:
    """Dynamically synthesizes Contra rules between all declared entity accounts.

    Matches transactions containing self-identity (self_patterns / self_vpas)
    and target bank tokens.

    Confidence values are read from the entity config (``contra_confidence`` and
    ``self_transfer_confidence``) so they can be tuned per-entity without code
    changes.
    """
    accounts = entity_config.get("accounts", [])
    if not accounts or not isinstance(accounts, list):
        return []

    self_pats = entity_config.get("self_patterns", [])
    self_vpas = entity_config.get("self_vpas", [])
    all_self_strs = list(self_pats) + [re.escape(v) for v in self_vpas]

    if not all_self_strs:
        name = entity_config.get("display_name", "")
        ent_id = entity_config.get("entity_id", "")
        if name:
            all_self_strs.append(re.escape(name))
        if ent_id:
            all_self_strs.append(r"\b" + re.escape(ent_id) + r"\b")

    if not all_self_strs:
        return []

    self_regexes = [re.compile(p, re.IGNORECASE) for p in all_self_strs]

    # Confidence values configurable per entity; fall back to scoring.json
    from tax_automation.config_loader import get_scoring_config

    synth_defaults = get_scoring_config().get("synthesized_rule_defaults", {})
    contra_conf = float(
        entity_config.get(
            "contra_confidence", synth_defaults.get("contra_confidence", 0.92)
        )
    )
    self_xfer_conf = float(
        entity_config.get(
            "self_transfer_confidence",
            synth_defaults.get("self_transfer_confidence", 0.88),
        )
    )

    from tax_automation.config_loader import get_pivot_category_config

    contra_prefix = (
        get_pivot_category_config().get("contra_label_prefix", "Contra -").strip()
    )

    contra_rules = []
    current_key = current_account_key.lower()

    for acc in accounts:
        tgt_key = acc.get("account_key", "").lower()
        if not tgt_key or tgt_key == current_key:
            continue

        tgt_bank = acc.get("bank", tgt_key).lower()
        tgt_acc_id = acc.get("account_id", tgt_key.upper())
        tgt_disp = acc.get("display_name", tgt_bank.upper())

        # Build bank tokens to match target account
        bank_tokens = list(_get_bank_alias_tokens(tgt_bank))
        # Include account digits if specific (e.g. "0333", "1227")
        acc_digits = re.findall(r"\d{3,}", tgt_acc_id)
        for d in acc_digits:
            bank_tokens.append(re.escape(d))

        same_bank = sum(
            a.get("bank", a.get("account_key", "")).lower() == tgt_bank
            for a in accounts
        )
        if same_bank > 1:
            bank_tokens = [re.escape(d) for d in acc_digits]
        bank_regexes = [re.compile(t, re.IGNORECASE) for t in bank_tokens]

        # Optional per-account exclusions (e.g. "HDFC SECURITIES" must not be
        # treated as a transfer to the HDFC savings account). Declared in the
        # entity's accounts[] entry as "exclude_patterns": [regex, ...].
        exclude_regexes = [
            re.compile(t, re.IGNORECASE) for t in acc.get("exclude_patterns", [])
        ]

        # Match function: narration has self-identity AND target bank token
        def make_contra_matcher(s_regs, b_regs, x_regs):
            return lambda p, dr, cr: (
                any(sr.search(p) for sr in s_regs)
                and any(br.search(p) for br in b_regs)
                and not any(xr.search(p) for xr in x_regs)
            )

        rule_label = f"{contra_prefix} {tgt_disp}"
        contra_rules.append(
            (
                rule_label,
                tgt_acc_id,
                make_contra_matcher(self_regexes, bank_regexes, exclude_regexes),
                contra_conf,
            )
        )

    # General self-transfer rule for any entity:
    # Catches transfers where the counterparty in UPI is self or marked as Self Transfer
    # even when the destination bank is omitted in the statement text (e.g. Kotak/GPay).
    self_xfer_pat = re.compile(r"\b(?:Self|Internal)\s*transfer\b", re.IGNORECASE)
    upi_self_pats = [
        re.compile(rf"UPI/(?:CR/|DR/)?.*{sr.pattern}", re.IGNORECASE)
        for sr in self_regexes
    ]

    def make_generic_self_matcher():
        return lambda p, dr, cr: bool(
            self_xfer_pat.search(p) or any(r.search(p) for r in upi_self_pats)
        )

    contra_rules.append(
        (
            f"{contra_prefix} Self Transfer",
            "Contra",
            make_generic_self_matcher(),
            self_xfer_conf,
        )
    )

    return contra_rules


def build_dynamic_family_rules(entity_config: dict[str, Any]) -> list[tuple]:
    """Dynamically synthesizes transfer rules for declared family members.

    Zero hardcoding in common rules: each taxpayer declares relatives in their config.
    The confidence value is read from ``family_transfer_confidence`` in entity config
    (default 0.90) so it can be tuned per-entity without code changes.
    """
    family = entity_config.get("family_members", [])
    if not family or not isinstance(family, list):
        return []

    family_conf = float(entity_config.get("family_transfer_confidence", 0.90))
    rules = []
    for member in family:
        name = member.get("name", "").strip()
        if not name:
            continue
        head = member.get("account_head", name)
        pats = member.get("patterns", [name])
        regexes = [re.compile(p, re.IGNORECASE) for p in pats]

        def make_family_matcher(regs):
            return lambda p, dr, cr: any(r.search(p) for r in regs)

        rules.append(
            (
                f"Transfer - {name}",
                head,
                make_family_matcher(regexes),
                family_conf,
            )
        )
    return rules


def build_dynamic_rent_rules(entity_config: dict[str, Any]) -> list[tuple]:
    """Dynamically synthesizes rent classification rules from entity configuration.

    The confidence value is read from ``rent_confidence`` in entity config
    (default 0.90) so it can be tuned per-entity without code changes.
    """
    rent = entity_config.get("rent")
    if not rent or not isinstance(rent, dict):
        return []

    landlords = rent.get("landlords", [])
    vpas = rent.get("vpas", [])
    keywords = rent.get("keywords", ["RENT"])
    all_tokens = landlords + vpas + keywords

    if not all_tokens:
        return []

    token_patterns = []
    for t in all_tokens:
        if t.isalnum() and r"\b" not in t:
            token_patterns.append(rf"\b{t}\b")
        else:
            token_patterns.append(t)

    regexes = [re.compile(t, re.IGNORECASE) for t in token_patterns]
    rent_conf = float(entity_config.get("rent_confidence", 0.90))

    def rent_matcher(p: str, dr: float, cr: float) -> bool:
        return dr > 0 and any(r.search(p) for r in regexes)

    return [("Rent", "Rent", rent_matcher, rent_conf)]


def build_dynamic_custom_rules(
    entity_config: dict[str, Any], layer: str = "entity"
) -> list[tuple]:
    """Compiles declarative custom rules declared in the entity configuration.

    Each rule may set ``"layer"``:
      - ``"entity"`` (default): evaluated first, before all other rules.
      - ``"common"``: evaluated after bank base rules, just before universal rules.
    """
    custom = entity_config.get("custom_rules", [])
    if not custom or not isinstance(custom, list):
        return []

    rules = []
    for r_dict in custom:
        if r_dict.get("layer", "entity").lower() != layer:
            continue
        try:
            compiled = _compile_declarative_rule(r_dict)
            rules.append(compiled)
        except Exception as exc:
            raise ValueError(f"Invalid entity rule: {r_dict}") from exc
    return rules


def build_rule_chain(
    entity_id: str, bank_key: str
) -> tuple[list[tuple], list[tuple], list[tuple]]:
    """Builds the full runtime rule chain for an entity and bank account.

    Returns a 3-tuple:
      - ``bank_rules``: entity-custom + rent + contra + family + bank-base rules
      - ``main_common_rules``: entity common-layer rules + universal common rules
        (excludes fallback rules — these run AFTER merchant detection)
      - ``fallback_rules``: generic UPI / "What is this?" rules (``is_fallback: true``)

    This separation means the pipeline can insert merchant detection between
    main_common_rules and fallback_rules without relying on a fragile
    ``len(rules) - 3`` offset.

    Layer 1: Entity custom rules, layer "entity" (exact amounts, specific overrides)
    Layer 2: Dynamic rent rules
    Layer 3: Dynamic contra rules (between accounts)
    Layer 4: Dynamic family member transfer rules
    Layer 5: Bank base rules
    Layer 6: Entity custom rules, layer "common"
    Layer 7: Universal common rules (main, then fallback)
    """
    entity_cfg = get_entity_config(entity_id)

    # Synthesize dynamic entity-specific rules
    custom_rules = build_dynamic_custom_rules(entity_cfg, layer="entity")
    rent_rules = build_dynamic_rent_rules(entity_cfg)
    contra_rules = build_dynamic_contra_rules(entity_cfg, bank_key)
    family_rules = build_dynamic_family_rules(entity_cfg)
    entity_common_rules = build_dynamic_custom_rules(entity_cfg, layer="common")

    # Bank base rules
    account = next(
        (a for a in entity_cfg.get("accounts", [])
         if a["account_key"].lower() == bank_key.lower()), None
    )
    bank_type = account.get("bank", bank_key) if account else bank_key
    bank_base = load_bank_rules(bank_type)

    # Assemble bank-level rules (evaluated before common rules)
    full_bank_rules = (
        custom_rules + rent_rules + contra_rules + family_rules + bank_base
    )

    # Universal common rules, preceded by entity common-layer rules.
    # FALLBACK_RULES (generic UPI / "What is this?") are returned separately
    # so the pipeline can insert merchant detection before them.
    common = get_declarative_common_rules()
    full_main_common = entity_common_rules + [
        _compile_declarative_rule(r) for r in common if not r.get("is_fallback")
    ]
    full_fallback = [
        _compile_declarative_rule(r) for r in common if r.get("is_fallback")
    ]

    return full_bank_rules, full_main_common, full_fallback
