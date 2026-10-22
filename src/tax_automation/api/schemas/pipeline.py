# -*- coding: utf-8 -*-
"""Pydantic schemas for pipeline operation endpoints."""

from __future__ import annotations
from pydantic import BaseModel


class PipelineRunRequest(BaseModel):
    input_path: str | None = None
    output_path: str | None = None


class PipelineJobResponse(BaseModel):
    entity_id: str
    fy: str
    status: str
    output_path: str | None = None
    message: str | None = None


class ConsolidateResponse(BaseModel):
    entity_id: str
    fy: str
    status: str
    output_path: str
    message: str


class ProcessResponse(BaseModel):
    entity_id: str
    fy: str
    status: str
    output_path: str
    message: str


class RunAllResponse(BaseModel):
    entity_id: str
    fy: str
    consolidate: ConsolidateResponse
    process: ProcessResponse
