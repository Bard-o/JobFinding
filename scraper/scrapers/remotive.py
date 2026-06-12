"""Scraper para la API publica de Remotive.

Remotive.com ofrece una API JSON sin autenticacion en:
https://remotive.com/api/remote-jobs

Solo incluye jobs relevantes para LATAM filtrados por location.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

import requests
import structlog
from bs4 import BeautifulSoup

from scraper.models import JobData

logger = structlog.get_logger(__name__)

REMOTIVE_API_URL = "https://remotive.com/api/remote-jobs"
CATEGORY = "software-development"
LIMIT = 100

LATAM_KEYWORDS = [
    "latam", "latin america", "latin america", "sudamerica",
    "argentina", "brasil", "brazil", "chile", "colombia",
    "mexico", "peru", "uruguay", "paraguay", "ecuador",
    "remote", "worldwide", "anywhere", "latin", "south america",
]

WORK_TYPE_MAP: dict[str, str] = {
    "full_time": "onsite",
    "contract": "contract",
    "part_time": "part_time",
    "freelance": "freelance",
    "internship": "internship",
}

_REMOTE_INDICATORS = {
    "remote", "worldwide", "anywhere",
    # Broad regional terms mean "work from anywhere in this region" = remote
    "latam", "latin america", "south america", "sudamerica", "latin",
}


def is_latam(location: str | None) -> bool:
    """Check if job location is relevant for LATAM."""
    if not location:
        return False
    loc_lower = location.lower()
    return any(kw in loc_lower for kw in LATAM_KEYWORDS)


def _normalize_work_type(job_type: str, location: str | None) -> str:
    """Normalize Remotive job_type to our work_type enum.

    Full-time jobs in remote/worldwide/anywhere locations are classified
    as 'remote'. Full-time jobs with specific country locations default
    to 'onsite'. Other job types map through WORK_TYPE_MAP.
    """
    location_lower = location.lower() if location else ""
    if job_type == "full_time":
        if any(indicator in location_lower for indicator in _REMOTE_INDICATORS) or not location:
            return "remote"
        return "onsite"
    return WORK_TYPE_MAP.get(job_type, "onsite")


def _parse_date(date_str: str | None) -> date | None:
    """Parse Remotive date string to date object."""
    if not date_str:
        return None
    try:
        return datetime.fromisoformat(date_str.replace("Z", "+00:00")).date()
    except (ValueError, AttributeError):
        return None


def _clean_description(html: str) -> str:
    """Strip HTML tags from description, leaving plain text."""
    if not html:
        return ""
    soup = BeautifulSoup(html, "lxml")
    return soup.get_text(separator=" ", strip=True)


def _job_from_json(job_json: dict[str, Any]) -> JobData | None:
    """Convert a Remotive job JSON to JobData.

    Returns None if the job is not LATAM-relevant or missing required fields.
    """
    location = job_json.get("candidate_required_location", "")

    if not is_latam(location):
        return None

    title = job_json.get("title", "").strip()
    company = job_json.get("company_name", "").strip()
    url = job_json.get("url", "").strip()

    if not title or not company or not url:
        return None

    return JobData(
        title=title,
        company=company,
        url=url,
        published_at=_parse_date(job_json.get("publication_date")),
        country=location or None,
        work_type=_normalize_work_type(
            job_json.get("job_type", "full_time"),
            location,
        ),
        seniority=None,
        salary_raw=None,
        description=_clean_description(job_json.get("description", "")),
        tags=job_json.get("tags") or [],
    )


def fetch_jobs(limit: int = LIMIT) -> list[JobData]:
    """Fetch jobs from Remotive API filtered for LATAM.

    Args:
        limit: Maximum number of jobs to fetch per API call (default 100).

    Returns:
        List of JobData objects for LATAM-relevant jobs.
    """
    params = {
        "category": CATEGORY,
        "limit": limit,
    }

    logger.info("remotive_fetch_start", params=params)

    try:
        response = requests.get(REMOTIVE_API_URL, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
    except requests.RequestException as e:
        logger.error("remotive_fetch_error", error=str(e))
        return []

    raw_jobs = data.get("jobs", [])
    jobs: list[JobData] = []

    for raw in raw_jobs:
        job = _job_from_json(raw)
        if job:
            jobs.append(job)

    logger.info("remotive_fetch_complete", total_raw=len(raw_jobs), latam=len(jobs))
    return jobs


class RemotiveScraper:
    """Scraper for the Remotive public API."""

    def __init__(self, limit: int = LIMIT) -> None:
        self.limit = limit

    def run(self) -> list[JobData]:
        """Fetch and return all LATAM jobs from Remotive.

        Returns:
            List of JobData objects.
        """
        return fetch_jobs(limit=self.limit)