# -*- coding: utf-8 -*-
"""Pydantic schemas for entity management endpoints."""

from __future__ import annotations
from typing import Any
from pydantic import BaseModel, Field


class RentConfig(BaseModel):
    landlords: list[str] = Field(default_factory=list)
    vpas: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)


class FamilyMember(BaseModel):
    name: str
    account_head: str | None = None
    patterns: list[str] = Field(default_factory=list)


class AccountConfig(BaseModel):
    account_key: str
    bank: str
    account_id: str
    display_name: str | None = None
    sheet_name: str | None = None
    meta_signals_extra: list[str] = Field(default_factory=list)


class CreateEntityRequest(BaseModel):
    entity_id: str = Field(
        ..., pattern=r"^[a-z0-9_]+$", description="Lowercase alphanumeric entity ID"
    )
    display_name: str = Field(..., description="Full legal name of taxpayer")
    pan: str | None = Field(default=None, description="PAN number")
    fy: str = Field(default="FY26", description="Initial Financial Year to scaffold")


class UpdateEntityRequest(BaseModel):
    display_name: str | None = None
    pan: str | None = None
    self_patterns: list[str] | None = None
    self_vpas: list[str] | None = None
    family_members: list[FamilyMember] | None = None
    rent: RentConfig | None = None
    custom_rules: list[dict[str, Any]] | None = None
    accounts: list[AccountConfig] | None = None
    output_sheet_names: list[str] | None = None


class EntityResponse(BaseModel):
    entity_id: str
    display_name: str
    pan: str | None = None
    self_patterns: list[str] = Field(default_factory=list)
    self_vpas: list[str] = Field(default_factory=list)
    family_members: list[dict[str, Any]] = Field(default_factory=list)
    rent: dict[str, Any] = Field(default_factory=dict)
    custom_rules: list[dict[str, Any]] = Field(default_factory=list)
    accounts: list[dict[str, Any]] = Field(default_factory=list)
    output_sheet_names: list[str] = Field(default_factory=list)
