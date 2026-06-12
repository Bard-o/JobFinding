"""Pydantic schemas for technology-related endpoints."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class TechnologyWithCount(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str
    category: str
    count: int


class TechnologyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    category: str


class TechnologyTrend(BaseModel):
    name: str
    category: str
    data: list[dict]  # [{"date": "2024-01-01", "count": 10}, ...]