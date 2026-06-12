"""Get on Board REST API client.

Uses the public API v0 to fetch job listings with pagination.
No authentication required for public search endpoints.

API docs: https://www.getonbrd.com/api-doc.html
Base URL: https://www.getonbrd.com/api/v0/
"""

from __future__ import annotations

import time
from datetime import date, datetime
from typing import Iterator

import requests
import structlog

from scraper.models import JobData

logger = structlog.get_logger(__name__)

# Public search endpoint
API_BASE = "https://www.getonbrd.com/api/v0"
SEARCH_URL = f"{API_BASE}/search/jobs"

# Seniority mapping (fetched once, cached)
SENIORITY_MAP: dict[int, str] = {}

# Company name lookup (cached per company_id)
COMPANY_CACHE: dict[int, str] = {}


def _fetch_company_name(company_id: int) -> str:
    """Fetch company name by ID, with caching to avoid duplicate API calls.

    Args:
        company_id: The company ID from the API.

    Returns:
        The company name, or empty string if not found.
    """
    if company_id in COMPANY_CACHE:
        return COMPANY_CACHE[company_id]

    try:
        resp = requests.get(
            f"{API_BASE}/companies/{company_id}",
            params={"lang": "en"},
            timeout=15,
            verify=False,
        )
        resp.raise_for_status()
        data = resp.json()
        name = data.get("data", {}).get("attributes", {}).get("name", "")
        COMPANY_CACHE[company_id] = name
        logger.debug("company_name_fetched", company_id=company_id, name=name)
        return name
    except Exception as e:
        logger.warning("company_fetch_failed", company_id=company_id, error=str(e))
        COMPANY_CACHE[company_id] = ""
        return ""


def fetch_seniorities() -> dict[int, str]:
    """Fetch seniority levels from the API and cache them.

    Returns:
        Dict mapping seniority ID to name (e.g. {4: "Senior", 5: "Lead"}).
    """
    global SENIORITY_MAP
    if SENIORITY_MAP:
        return SENIORITY_MAP

    try:
        resp = requests.get(f"{API_BASE}/seniorities", timeout=15)
        resp.raise_for_status()
        data = resp.json()
        for item in data.get("data", []):
            sid = item.get("id")
            name = item.get("attributes", {}).get("name", "").lower()
            if sid and name:
                SENIORITY_MAP[sid] = name
        logger.info("seniorities_fetched", count=len(SENIORITY_MAP))
    except Exception as e:
        logger.warning("seniorities_fetch_failed", error=str(e))
        # Fallback common mappings
        SENIORITY_MAP = {1: "junior", 2: "junior", 3: "mid", 4: "senior", 5: "lead"}

    return SENIORITY_MAP


def _unix_to_date(unix_ts: int) -> date | None:
    """Convert Unix timestamp to date."""
    if not unix_ts:
        return None
    try:
        return datetime.fromtimestamp(unix_ts).date()
    except (ValueError, OSError):
        return None


def fetch_jobs(
    country_code: str = "CL",
    per_page: int = 120,
    lang: str = "en",
    rate_limit: float = 1.0,
) -> Iterator[JobData]:
    """Fetch jobs from the public search API with pagination.

    Yields JobData objects one by one, fetching new pages as needed.
    Rate limits requests to avoid overwhelming the API.

    Args:
        country_code: ISO 3166-1 alpha-2 country code (e.g. CL, CO, AR).
        per_page: Results per page (max 120).
        lang: Response language (en, es, pt).
        rate_limit: Minimum seconds between API calls.

    Yields:
        JobData objects for each job found.
    """
    page = 1
    seniorities = fetch_seniorities()

    while True:
        params = {
            "country_code": country_code,
            "per_page": min(per_page, 120),
            "page": page,
            "lang": lang,
            "expand[]": "company",
        }

        logger.info("api_fetch_start", page_num=page, country=country_code, per_page=per_page, lang=lang)
        time.sleep(rate_limit)

        try:
            resp = requests.get(SEARCH_URL, params=params, timeout=30, verify=False)
            resp.raise_for_status()
        except requests.HTTPError as e:
            logger.error("api_http_error", status=e.response.status_code, error=str(e))
            break

        data = resp.json()
        jobs_list = data.get("data", [])
        meta = data.get("meta", {})
        total_pages = meta.get("total_pages", 1)

        if not jobs_list:
            logger.info("api_page_empty", page=page)
            break

        for item in jobs_list:
            job = _parse_api_job(item, seniorities)
            if job:
                yield job

        logger.info(
            "api_page_done",
            page_num=page,
            total_pages=total_pages,
            jobs_in_page=len(jobs_list),
        )

        if page >= total_pages:
            break

        page += 1


def _parse_api_job(item: dict, seniorities: dict[int, str]) -> JobData | None:
    """Parse a single job item from the API response.

    Args:
        item: The 'data' entry from the API response.
        seniorities: Dict mapping seniority ID to name.

    Returns:
        JobData instance, or None if required fields are missing.
    """
    try:
        attrs = item.get("attributes", {})
        job_id = item.get("id", "")
        links = item.get("links", {})
        public_url = links.get("public_url", f"https://www.getonbrd.com/jobs/{job_id}")

        # Published at (Unix timestamp)
        published_ts = attrs.get("published_at")
        published_at = _unix_to_date(published_ts) if published_ts else None

        # Work type
        remote = attrs.get("remote", False)
        remote_modality = attrs.get("remote_modality", "")
        if remote:
            work_type = "remote"
        elif remote_modality in ("no_remote", ""):
            work_type = "onsite"
        else:
            work_type = "hybrid"

        # Seniority
        seniority_id = None
        seniority_data = attrs.get("seniority", {})
        if isinstance(seniority_data, dict):
            inner = seniority_data.get("data", {})
            if isinstance(inner, dict):
                seniority_id = inner.get("id")
            else:
                seniority_id = seniority_data.get("id")
        seniority = seniorities.get(seniority_id) if seniority_id else None

        # Country
        countries = attrs.get("countries", [])
        country = countries[0] if countries else None

        # Company name (from /companies/{id} endpoint, cached)
        company_id = None
        company_data = attrs.get("company", {})
        if isinstance(company_data, dict):
            # API returns {data: {id: X, type: 'company'}} or {data: {...}}
            inner = company_data.get("data", {})
            if isinstance(inner, dict):
                company_id = inner.get("id")
            else:
                company_id = company_data.get("id")
        company = _fetch_company_name(company_id) if company_id else ""

        # Tags (not available in search endpoint without expand)
        tags: list[str] = []

        job = JobData(
            title=attrs.get("title", ""),
            company=company,
            url=public_url,
            published_at=published_at,
            country=country,
            work_type=work_type,
            seniority=seniority,
            salary_raw=None,
            description=attrs.get("description"),
            tags=tags,
        )

        logger.debug("api_job_parsed", job_id=job_id, title=job.title, url=job.url)
        return job

    except Exception as e:
        logger.warning("api_job_parse_error", item_id=item.get("id"), error=str(e))
        return None