"""Data transfer objects for the scraper pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime


@dataclass
class SitemapEntry:
    """A single URL entry parsed from the sitemap.

    Attributes:
        url: The full URL (e.g. https://www.getonboard.com/jobs/...).
        lastmod: Last modification timestamp from the sitemap, if available.
    """

    url: str
    lastmod: datetime | None


@dataclass
class JobData:
    """Extracted structured data from a GetOnBoard job detail page.

    Attributes:
        title: Job title (required).
        company: Company name (required).
        country: Country where the job is located.
        published_at: Publication date of the job listing.
        url: Normalized URL (/empleos/ replaced with /jobs/).
        work_type: "remote", "hybrid", or "onsite".
        seniority: "junior", "mid", "senior", or "lead".
        salary_raw: Raw salary string as shown on the page.
        description: Job description text.
        tags: Raw technology tag slugs from the page.
    """

    title: str
    company: str
    url: str
    published_at: date | None = None
    country: str | None = None
    work_type: str | None = None
    seniority: str | None = None
    salary_raw: str | None = None
    description: str | None = None
    tags: list[str] = field(default_factory=list)
