# -*- coding: utf-8 -*-
"""loader.py.

Dynamic rule chain compiler:
Assembles runtime classification rules combining:
1. Dynamic Entity Custom Rules (exact amounts, specific overrides)
2. Dynamic Rent Rules (synthesized from entity_config["rent"])
3. Dynamic Contra Rules (synthesized from entity_config["accounts"] + self identity)
4. Dynamic Family Transfer Rules (synthesized from entity_config["family_members"])
5. Python Entity Extensions (optional entity_extensions/<entity>_rules.py)
6. Bank Base Rules (loaded directly from config/banks/<bank>.json rules_module)
7. Agnostic Common Rules (from config/rules_common.json)
"""

from __future__ import annotations
import importlib
import re
from typing import Any

from tax_automation.config_loader import (
    get_bank_schema,
    get_entity_config,
)
from tax_automation.rules.common_base import RULES_COMMON, _compile_declarative_rule

_BANK_RULES_CACHE: dict[str, list[tuple]] = {}
_EXT_CACHE: dict[str, dict[str, list[tuple]]] = {}

# Standard bank alias tokens used for dynamic Contra synthesis
_BANK_ALIAS_TOKENS: dict[str, list[str]] = {
    "sbi": [r"\bSBI\b", r"\bSBIN\b", r"STATE\s*BANK\s*OF\s*INDIA", r"STATE\s*BANK"],
    "kotak": [r"\bKOTAK\b", r"\bKKBK\b"],
    "hdfc": [r"\bHDFC\b"],
    "axis": [r"\bAXIS\b", r"\bUTIB\b"],
    "boi": [r"\bBOI\b", r"\bBKID\b", r"BANK\s*OF\s*INDIA"],
    "federal": [r"\bFEDERAL\b", r"\bFDRL\b", r"\bJUPITER\b"],
    "sbm": [r"\bSBM\b", r"\bSTCB\b"],
    "icici": [r"\bICICI\b", r"\bICIC\b"],
}


def load_entity_extensions(entity_id: str) -> dict[str, list[tuple]]:
    """Loads optional Python entity rule extensions from
    entity_extensions/<entity>_rules.py.
    """
    if entity_id in _EXT_CACHE:
        return _EXT_CACHE[entity_id]

    module_name = f"tax_automation.rules.entity_extensions.{entity_id.lower()}_rules"
    try:
        mod = importlib.import_module(module_name)
        ext = getattr(mod, "EXTRA_RULES", {})
    except (ImportError, AttributeError):
        ext = {}

    _EXT_CACHE[entity_id] = ext
    return ext


def load_bank_rules(
    bank_key: str, rules_module: str | None = None
) -> list[tuple]:
    """Loads bank base classification rules dynamically without hardcoded maps.

    If rules_module is not specified, resolves it directly from the bank's schema JSON.
    """
    key = bank_key.lower()
    if key in _BANK_RULES_CACHE:
        return _BANK_RULES_CACHE[key]

    module_name = rules_module
    if not module_name:
        schema = get_bank_schema(key)
        module_name = schema.get("rules_module")

    if not module_name:
        # Fallback convention
        module_name = f"tax_automation.rules.banks.{key}"

    try:
        mod = importlib.import_module(module_name)
        rules = []
        # Look for RULES_<NAME> attribute
        for var_name in dir(mod):
            if var_name.startswith("RULES_") and isinstance(
                getattr(mod, var_name), list
            ):
                rules = getattr(mod, var_name)
                break
    except (ImportError, AttributeError):
        rules = []

    _BANK_RULES_CACHE[key] = rules
    return rules


def build_dynamic_contra_rules(
    entity_config: dict[str, Any], current_account_key: str
) -> list[tuple]:
    """Dynamically synthesizes Contra rules between all declared entity accounts.

    Matches transactions containing self-identity (self_patterns / self_vpas)
    and target bank tokens.
    """
    accounts = entity_config.get("accounts", [])
    if not accounts or not isinstance(accounts, list):
        return []

    self_pats = entity_config.get("self_patterns", [])
    self_vpas = entity_config.get("self_vpas", [])
    all_self_strs = list(self_pats) + list(self_vpas)

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
        bank_tokens = list(_BANK_ALIAS_TOKENS.get(tgt_bank, [tgt_bank]))
        # Include account digits if specific (e.g. "0333", "1227")
        acc_digits = re.findall(r"\d{3,}", tgt_acc_id)
        for d in acc_digits:
            bank_tokens.append(re.escape(d))

        bank_regexes = [re.compile(t, re.IGNORECASE) for t in bank_tokens]

        # Match function: narration has self-identity AND target bank token
        def make_contra_matcher(s_regs, b_regs):
            return lambda p, dr, cr: (
                any(sr.search(p) for sr in s_regs)
                and any(br.search(p) for br in b_regs)
            )

        rule_label = f"Contra - {tgt_disp}"
        contra_rules.append(
            (
                rule_label,
                tgt_acc_id,
                make_contra_matcher(self_regexes, bank_regexes),
                0.92,
            )
        )

    return contra_rules


def build_dynamic_family_rules(entity_config: dict[str, Any]) -> list[tuple]:
    """Dynamically synthesizes transfer rules for declared family members.

    Zero hardcoding in common rules: each taxpayer declares relatives in their config.
    """
    family = entity_config.get("family_members", [])
    if not family or not isinstance(family, list):
        return []

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
                0.90,
            )
        )
    return rules


def build_dynamic_rent_rules(entity_config: dict[str, Any]) -> list[tuple]:
    """Dynamically synthesizes rent classification rules from entity configuration."""
    rent = entity_config.get("rent")
    if not rent or not isinstance(rent, dict):
        return []

    landlords = rent.get("landlords", [])
    vpas = rent.get("vpas", [])
    keywords = rent.get("keywords", ["RENT"])
    all_tokens = landlords + vpas + keywords

    if not all_tokens:
        return []

    regexes = [re.compile(t, re.IGNORECASE) for t in all_tokens]

    def rent_matcher(p: str, dr: float, cr: float) -> bool:
        return dr > 0 and any(r.search(p) for r in regexes)

    return [("Rent", "Rent", rent_matcher, 0.90)]


def build_dynamic_custom_rules(entity_config: dict[str, Any]) -> list[tuple]:
    """Compiles declarative custom rules declared in the entity configuration."""
    custom = entity_config.get("custom_rules", [])
    if not custom or not isinstance(custom, list):
        return []

    rules = []
    for r_dict in custom:
        try:
            compiled = _compile_declarative_rule(r_dict)
            rules.append(compiled)
        except Exception:
            continue
    return rules


def build_rule_chain(
    entity_id: str, bank_key: str
) -> tuple[list[tuple], list[tuple]]:
    """Builds the full runtime rule chain for an entity and bank account.

    Layer 1: Entity custom rules (exact amounts, specific overrides)
    Layer 2: Dynamic rent rules
    Layer 3: Dynamic contra rules (between accounts)
    Layer 4: Dynamic family member transfer rules
    Layer 5: Entity extension Python rules (if any)
    Layer 6: Bank base rules
    Layer 7: Universal common rules
    """
    entity_cfg = {}
    try:
        entity_cfg = get_entity_config(entity_id)
    except Exception:
        pass

    # Synthesize dynamic entity-specific rules
    custom_rules = build_dynamic_custom_rules(entity_cfg)
    rent_rules = build_dynamic_rent_rules(entity_cfg)
    contra_rules = build_dynamic_contra_rules(entity_cfg, bank_key)
    family_rules = build_dynamic_family_rules(entity_cfg)

    # Legacy Python extensions (if present)
    ext = load_entity_extensions(entity_id)
    bank_ext = ext.get(bank_key.lower(), [])
    common_ext = ext.get("common", [])

    # Bank base rules
    bank_base = load_bank_rules(bank_key)

    # Assemble bank-level rules (evaluated before common rules)
    full_bank_rules = (
        custom_rules
        + rent_rules
        + contra_rules
        + family_rules
        + bank_ext
        + bank_base
    )

    # Universal common rules
    full_common_rules = common_ext + RULES_COMMON

    return full_bank_rules, full_common_rules
