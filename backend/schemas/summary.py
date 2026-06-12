"""Pydantic schemas for summary endpoint."""

from __future__ import annotations

from datetime import date
from typing import Dict, List, Optional

from pydantic import BaseModel


class TopTechnology(BaseModel):
    name: str
    category: str
    count: int


class SummaryResponse(BaseModel):
    snapshot_date: Optional[date] = None
    total_jobs: int
    total_companies: int
    jobs_by_source: Dict[str, int] = {}
    jobs_by_seniority: Dict[str, int] = {}
    jobs_by_work_type: Dict[str, int] = {}
    top_technologies: List[TopTechnology] = []