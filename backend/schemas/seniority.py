"""Pydantic schemas for seniority distribution."""

from __future__ import annotations

from typing import Dict

from pydantic import BaseModel


class SeniorityDistributionResponse(BaseModel):
    distribution: Dict[str, int]
    total: int