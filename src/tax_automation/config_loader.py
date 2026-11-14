# -*- coding: utf-8 -*-
"""config_loader.py.

Dynamic loader for JSON configurations, bank schemas, entity profiles,
and canonical directory path resolution.
"""

from __future__ import annotations
import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Any

# Find repository root directory
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
CONFIG_DIR = REPO_ROOT / "config"


@lru_cache(maxsize=128)
def _read_json_version(path: str, content: str) -> Any:
    return json.loads(content)


def read_config(path: Path) -> Any:
    """Content-keyed cache: edits take effect without restarting the API."""
    return _read_json_version(str(path), path.read_text(encoding="utf-8"))


def validate_config(value: Any, schema_name: str, source: Path) -> None:
    from jsonschema import Draft7Validator

    schema = read_config(CONFIG_DIR / "schemas" / schema_name)
    errors = sorted(Draft7Validator(schema).iter_errors(value), key=str)
    if errors:
        error = errors[0]
        location = ".".join(map(str, error.absolute_path))
        raise ValueError(f"{source}:{location}: {error.message}")


def load_env_file(env_path: Path | None = None) -> dict[str, str]:
    """Loads key=value pairs from a .env file into environment variables."""
    if env_path is None:
        env_path = REPO_ROOT / ".env"

    env_vars = {}
    if env_path.exists():
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    k, v = line.split("=", 1)
                    k, v = k.strip(), v.strip()
                    os.environ[k] = v
                    env_vars[k] = v
    return env_vars


def get_entity_config(entity_id: str) -> dict[str, Any]:
    """Loads entity profile configuration JSON from config/entities/<entity>.json."""
    config_file = CONFIG_DIR / "entities" / f"{entity_id.lower()}.json"
    if not config_file.exists():
        raise FileNotFoundError(
            f"Entity configuration file not found at: {config_file}"
        )

    config = read_config(config_file)
    validate_config(config, "entity.json", config_file)
    return config


def get_consolidation_map(entity_id: str, fy: str) -> dict[str, Any]:
    """Loads statement consolidation map JSON from
    config/consolidation/<entity>_<fy>.json.
    """
    map_file = CONFIG_DIR / "consolidation" / f"{entity_id.lower()}_{fy.lower()}.json"
    if not map_file.exists():
        raise FileNotFoundError(f"Consolidation map file not found at: {map_file}")

    with open(map_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data


def resolve_password(password_env_var: str | None) -> str | None:
    """Resolves statement password from environment variable."""
    if not password_env_var:
        return None
    load_env_file()
    return os.environ.get(password_env_var)


def get_bank_schema(bank_key: str) -> dict[str, Any]:
    """Loads base bank column schema and signals from config/banks/<bank_key>.json."""
    schema_file = CONFIG_DIR / "banks" / f"{bank_key.lower()}.json"
    if not schema_file.exists():
        raise FileNotFoundError(f"Unknown bank configuration: {schema_file}")

    schema = read_config(schema_file)
    for field in ("col_date", "col_particulars"):
        if not schema.get(field):
            raise ValueError(f"{schema_file}: missing {field}")
    if not (schema.get("col_dr") or schema.get("col_cr")):
        raise ValueError(f"{schema_file}: missing debit/credit column mapping")
    validate_config({"rules": schema.get("rules", [])}, "rules.json", schema_file)
    return schema


def resolve_entity_bank_registry(entity_id: str) -> dict[str, dict[str, Any]]:
    """Constructs the complete runtime bank registry for an entity.

    Merges each account declared in the entity profile with its base bank schema.
    """
    config = get_entity_config(entity_id)
    registry: dict[str, dict[str, Any]] = {}

    # Case 1: Declarative accounts list (Target Architecture)
    if "accounts" in config and isinstance(config["accounts"], list):
        for acc in config["accounts"]:
            acc_key = acc.get("account_key", "").lower()
            if not acc_key:
                raise ValueError("Every account requires an account_key")
            if acc_key in registry:
                raise ValueError(f"Duplicate account_key: {acc_key}")
            bank_type = acc.get("bank", acc_key).lower()
            base_schema = get_bank_schema(bank_type)

            merged = dict(base_schema)
            # Overlay account-specific configuration
            merged["account_id"] = acc.get("account_id", acc_key.upper())
            merged["display_name"] = acc.get(
                "display_name", base_schema.get("display_name", acc_key.title())
            )
            merged["sheet_name"] = acc.get("sheet_name", acc_key.title())
            merged["bank_type"] = bank_type
            merged["account_signals"] = acc.get("meta_signals_extra", [])

            # Extend metadata signals with account-specific branch/id signals
            extra_signals = acc.get("meta_signals_extra", [])
            if extra_signals:
                existing_sigs = list(merged.get("meta_signals", []))
                merged["meta_signals"] = existing_sigs + [
                    s for s in extra_signals if s not in existing_sigs
                ]

            registry[acc_key] = merged

    return registry


def resolve_input_dir(
    entity_id: str, fy: str, subfolder: str = "bank_statements"
) -> Path:
    """Returns canonical input directory path: data/<entity>/<FY>/input/<subfolder>/."""
    path = REPO_ROOT / "data" / entity_id.lower() / fy.upper() / "input" / subfolder
    path.mkdir(parents=True, exist_ok=True)
    return path


def resolve_output_dir(entity_id: str, fy: str) -> Path:
    """Returns canonical output directory path: data/<entity>/<FY>/output/."""
    path = REPO_ROOT / "data" / entity_id.lower() / fy.upper() / "output"
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_merchants_config() -> list[dict[str, Any]]:
    """Loads merchant mappings from config/merchants.json."""
    m_file = CONFIG_DIR / "merchants.json"
    if not m_file.exists():
        return []
    return read_config(m_file)


def get_cc_categories_config() -> dict[str, Any]:
    """Loads CC category mappings and regex signals from config/cc_categories.json."""
    c_file = CONFIG_DIR / "cc_categories.json"
    if not c_file.exists():
        return {}
    with open(c_file, "r", encoding="utf-8") as f:
        return json.load(f)


def get_header_keywords_config() -> dict[str, list[str]]:
    """Loads header row keyword sets from config/header_keywords.json."""
    h_file = CONFIG_DIR / "header_keywords.json"
    if not h_file.exists():
        return {}
    with open(h_file, "r", encoding="utf-8") as f:
        return json.load(f)


def get_exporter_theme_config() -> dict[str, Any]:
    """Loads Excel exporter theme & styling settings from config/exporter_theme.json."""
    e_file = CONFIG_DIR / "exporter_theme.json"
    if not e_file.exists():
        return {}
    with open(e_file, "r", encoding="utf-8") as f:
        return json.load(f)


def get_declarative_common_rules() -> list[dict[str, Any]]:
    """Loads common classification rules from config/rules_common.json."""
    r_file = CONFIG_DIR / "rules_common.json"
    if not r_file.exists():
        return []
    rules = read_config(r_file)
    validate_config(rules, "rules.json", r_file)
    return rules


def get_scoring_config() -> dict[str, Any]:
    """Loads numeric scoring thresholds from config/scoring.json.

    Contains bank identification weights, confidence band thresholds, and
    default confidence values for synthesized rules.  All magic numbers that
    were previously baked into Python source code are now read from here.
    """
    s_file = CONFIG_DIR / "scoring.json"
    if not s_file.exists():
        return {}
    with open(s_file, "r", encoding="utf-8") as f:
        return json.load(f)


def get_pivot_category_config() -> dict[str, Any]:
    """Loads pivot category definitions from config/pivot_category_map.json.

    Contains:
    - ``payment_categories``: ordered list of payment row labels for the Monthly Pivot
    - ``receipt_categories``: ordered list of receipt row labels
    - ``head_to_payment_category``: account_head → pivot category for DR rows
    - ``narration_to_payment_category``: narration label → pivot category for DR rows
    - ``head_to_receipt_category``: account_head → pivot category for CR rows
    - ``narration_to_receipt_category``: narration label → pivot category for CR rows
    - ``contra_label_prefix``: string prefix that identifies contra labels
      (default "Contra -")
    - ``cc_payment_narrations``: narration labels that map to "Credit Card Payment"
    """
    p_file = CONFIG_DIR / "pivot_category_map.json"
    if not p_file.exists():
        return {}
    with open(p_file, "r", encoding="utf-8") as f:
        return json.load(f)


def get_colour_legend_config() -> list[dict[str, Any]]:
    """Loads the colour legend group definitions from config/colour_legend.json.

    Returns a list of group dicts:
    ``[{"group": "...", "items": [{"label": "...", "description": "..."}]}]``
    """
    l_file = CONFIG_DIR / "colour_legend.json"
    if not l_file.exists():
        return []
    with open(l_file, "r", encoding="utf-8") as f:
        return json.load(f)
