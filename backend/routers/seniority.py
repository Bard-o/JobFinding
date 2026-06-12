"""Seniority distribution endpoint."""

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models.job import Job
from backend.schemas.seniority import SeniorityDistributionResponse

router = APIRouter(prefix="", tags=["seniority"])


@router.get("/seniority/distribution", response_model=SeniorityDistributionResponse)
def get_seniority_distribution(
    db: Session = Depends(get_db),
) -> SeniorityDistributionResponse:
    """Distribucion de seniority de los jobs."""
    results = db.query(
        func.coalesce(Job.seniority, "unknown"),
        func.count(Job.id),
    ).group_by(
        func.coalesce(Job.seniority, "unknown")
    ).all()

    distribution = {row[0]: row[1] for row in results}
    total = sum(distribution.values())

    return SeniorityDistributionResponse(
        distribution=distribution,
        total=total,
    )