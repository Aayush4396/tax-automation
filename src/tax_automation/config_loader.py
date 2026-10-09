# -*- coding: utf-8 -*-
"""
config_loader.py
================
Dynamic loader for JSON entity configurations, consolidation maps, and .env credentials.
"""

from __future__ import annotations
import os
import json
from pathlib import Path
from typing import Any

# Find repository root directory
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
CONFIG_DIR = REPO_ROOT / "config"


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

    with open(config_file, "r", encoding="utf-8") as f:
        config = json.load(f)
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


def get_merchants_config() -> list[dict[str, Any]]:
    """Loads merchant mappings from config/merchants.json."""
    m_file = CONFIG_DIR / "merchants.json"
    if not m_file.exists():
        return []
    with open(m_file, "r", encoding="utf-8") as f:
        return json.load(f)


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
    with open(r_file, "r", encoding="utf-8") as f:
        return json.load(f)
