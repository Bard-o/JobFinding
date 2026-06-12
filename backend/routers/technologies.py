"""Technologies endpoints."""

from __future__ import annotations

from datetime import date, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import and_, desc, func
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models.job import Job
from backend.models.job_technology import JobTechnology
from backend.models.technology import Technology
from backend.schemas.technology import TechnologyWithCount

router = APIRouter(prefix="", tags=["technologies"])


@router.get("/technologies", response_model=list[TechnologyWithCount])
def list_technologies(db: Session = Depends(get_db)) -> list[TechnologyWithCount]:
    """Lista de tecnologias con conteo de jobs que la usan."""
    results = (
        db.query(
            Technology.name,
            Technology.category,
            func.count(JobTechnology.job_id).label("count"),
        )
        .join(JobTechnology, JobTechnology.technology_id == Technology.id)
        .group_by(Technology.id, Technology.name, Technology.category)
        .order_by(desc("count"))
        .all()
    )

    return [
        TechnologyWithCount(name=r[0], category=r[1], count=r[2])
        for r in results
    ]


@router.get("/technologies/trends")
def get_technology_trends(
    days: int = Query(default=30, ge=7, le=365),
    db: Session = Depends(get_db),
) -> dict:
    """Evolucion temporal de tecnologias por dia en los ultimos N dias.

    Returns a dict: {technology_name: [{"date": "...", "count": 5}, ...]}
    """
    start_date = date.today() - timedelta(days=days)

    results = (
        db.query(
            Technology.name,
            func.date(Job.scraped_at).label("date"),
            func.count(func.distinct(Job.id)).label("count"),
        )
        .join(JobTechnology, JobTechnology.technology_id == Technology.id)
        .join(Job, Job.id == JobTechnology.job_id)
        .filter(
            and_(
                Job.scraped_at >= start_date,
                Job.scraped_at <= date.today(),
            )
        )
        .group_by(Technology.name, func.date(Job.scraped_at))
        .order_by(Technology.name, func.date(Job.scraped_at))
        .all()
    )

    trends: dict[str, list[dict]] = {}
    for tech_name, d, count in results:
        if tech_name not in trends:
            trends[tech_name] = []
        trends[tech_name].append({"date": d.isoformat(), "count": count})

    return {"days": days, "trends": trends}