"""Extract structured job data from GetOnBoard HTML pages.

Parses job detail pages using BeautifulSoup and returns JobData DTOs.
Also normalizes URLs to replace /empleos/ paths with /jobs/.
"""

from __future__ import annotations

import re
from datetime import date, datetime
from typing import List, Optional

import structlog
from bs4 import BeautifulSoup

from scraper.models import JobData

logger = structlog.get_logger(__name__)

# Pattern for extracting technology tags from /jobs/tag/{tag} links
TAG_PATTERN = re.compile(r"/jobs/tag/([^/]+)")

# Work type keywords mapped to normalized values
WORK_TYPE_PATTERNS: dict[str, str] = {
    "remote": "remote",
    "remoto": "remote",
    "hybrid": "hybrid",
    "híbrido": "hybrid",
    "hibrido": "hybrid",
    "onsite": "onsite",
    "presencial": "onsite",
    "in-office": "onsite",
}

# Seniority keywords mapped to normalized values
SENIORITY_PATTERNS: dict[str, str] = {
    "junior": "junior",
    "semi-senior": "mid",
    "semisenior": "mid",
    "semi senior": "mid",
    "mid": "mid",
    "middle": "mid",
    "senior": "senior",
    "lead": "lead",
    "principal": "lead",
    "staff": "lead",
}


def normalize_url(url: str) -> str:
    """Normalize a GetOnBoard URL by replacing /empleos/ with /jobs/.

    The sitemap may contain Spanish URLs with /empleos/ paths that point
    to the same job as the English /jobs/ variant. This normalization
    prevents duplicate entries in the database.

    Args:
        url: The raw URL from the sitemap or page.

    Returns:
        URL with /empleos/ replaced by /jobs/ in the path.
    """
    return url.replace("/empleos/", "/jobs/")


def extract_job(html: str, url: str) -> JobData:
    """Extract structured job data from a GetOnBoard job detail page.

    Parses the HTML using BeautifulSoup and extracts all available fields.
    Missing optional fields are set to None; required fields (title, company,
    url) are always populated.

    Args:
        html: The raw HTML content of the job detail page.
        url: The URL of the page (will be normalized).

    Returns:
        A JobData instance with all extracted fields.
    """
    soup = BeautifulSoup(html, "lxml")
    normalized = normalize_url(url)

    title = _extract_title(soup)
    company = _extract_company(soup)
    country = _extract_country(soup)
    published_at = _extract_published_at(soup)
    work_type = _extract_work_type(soup)
    seniority = _extract_seniority(soup)
    salary_raw = _extract_salary(soup)
    description = _extract_description(soup)
    tags = _extract_tags(soup)

    logger.debug(
        "job_extracted",
        title=title,
        company=company,
        url=normalized,
        tags_count=len(tags),
    )

    return JobData(
        title=title,
        company=company,
        url=normalized,
        published_at=published_at,
        country=country,
        work_type=work_type,
        seniority=seniority,
        salary_raw=salary_raw,
        description=description,
        tags=tags,
    )


def _extract_title(soup: BeautifulSoup) -> str:
    """Extract the job title from the page.

    Tries <h1> tags first, then falls back to og:title meta tag.
    Strips whitespace and returns an empty string if not found.
    """
    h1 = soup.find("h1")
    if h1 and h1.get_text(strip=True):
        return h1.get_text(strip=True)

    og_title = soup.find("meta", property="og:title")
    if og_title and og_title.get("content"):
        return og_title["content"].strip()

    return ""


def _extract_company(soup: BeautifulSoup) -> str:
    """Extract the company name from the page.

    Checks for a company-name class span first, then og:site_name meta,
    then falls back to text patterns.
    """
    company_el = soup.find("span", class_="company-name")
    if company_el and company_el.get_text(strip=True):
        return company_el.get_text(strip=True)

    # Fallback: look for itemprop="hiringOrganization" schema
    org = soup.find(attrs={"itemprop": "hiringOrganization"})
    if org:
        name_el = org.find(attrs={"itemprop": "name"})
        if name_el and name_el.get_text(strip=True):
            return name_el.get_text(strip=True)
        if org.get_text(strip=True):
            return org.get_text(strip=True)

    return ""


def _extract_country(soup: BeautifulSoup) -> Optional[str]:
    """Extract the country from the page.

    Checks for itemprop="country" meta, then text content of job-country div.
    """
    country_meta = soup.find("meta", attrs={"itemprop": "country"})
    if country_meta and country_meta.get("content"):
        return country_meta["content"].strip()

    country_div = soup.find("div", class_="job-country")
    if country_div:
        text = country_div.get_text(strip=True)
        # Strip flag emoji prefix (regional indicator symbols)
        text = re.sub(r"[\U0001F1E0-\U0001F1FF]+", "", text).strip()
        if text:
            return text

    return None


def _extract_published_at(soup: BeautifulSoup) -> Optional[date]:
    """Extract the publication date from the page.

    Tries <time> element with datetime attribute, then itemprop="datePublished"
    meta content, then text parsing.
    """
    time_el = soup.find("time", attrs={"datetime": True})
    if time_el:
        dt_str = time_el["datetime"]
        try:
            return _parse_date_string(dt_str)
        except (ValueError, TypeError):
            pass

    date_meta = soup.find("meta", attrs={"itemprop": "datePublished"})
    if date_meta and date_meta.get("content"):
        try:
            return _parse_date_string(date_meta["content"])
        except (ValueError, TypeError):
            pass

    return None


def _parse_date_string(s: str) -> date:
    """Parse a date string in common formats.

    Args:
        s: Date string to parse.

    Returns:
        A date object.

    Raises:
        ValueError: If the string cannot be parsed.
    """
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Cannot parse date: {s}")


def _extract_work_type(soup: BeautifulSoup) -> Optional[str]:
    """Extract the work type (remote/hybrid/onsite) from the page.

    Looks for badge elements and text content, matching against known patterns.
    """
    # Check badge elements first
    badge = soup.find("span", class_="work-type-badge")
    if badge:
        text = badge.get_text(strip=True).lower()
        for pattern, value in WORK_TYPE_PATTERNS.items():
            if pattern in text:
                return value

    # Fallback: search full page text for work type keywords
    page_text = soup.get_text(separator=" ").lower()
    for pattern, value in WORK_TYPE_PATTERNS.items():
        if pattern in page_text:
            return value

    return None


def _extract_seniority(soup: BeautifulSoup) -> Optional[str]:
    """Extract the seniority level from the page.

    Looks for badge elements and text content, matching against known patterns.
    """
    badge = soup.find("span", class_="seniority-badge")
    if badge:
        text = badge.get_text(strip=True).lower()
        for pattern, value in SENIORITY_PATTERNS.items():
            if pattern in text:
                return value

    # Fallback: search job title for seniority hints
    title_el = soup.find("h1")
    if title_el:
        title_text = title_el.get_text(strip=True).lower()
        for pattern, value in SENIORITY_PATTERNS.items():
            if pattern in title_text:
                return value

    return None


def _extract_salary(soup: BeautifulSoup) -> Optional[str]:
    """Extract the raw salary string from the page.

    Returns the full salary range text as-is for later processing.
    """
    salary_el = soup.find("span", class_="salary-range")
    if salary_el and salary_el.get_text(strip=True):
        return salary_el.get_text(strip=True)

    # Fallback: look for common salary patterns in div.job-salary
    salary_div = soup.find("div", class_="job-salary")
    if salary_div:
        text = salary_div.get_text(strip=True)
        if text:
            return text

    return None


def _extract_description(soup: BeautifulSoup) -> Optional[str]:
    """Extract the job description from the page.

    Tries og:description meta first, then meta description, then
    the job-description div content.
    """
    og_desc = soup.find("meta", property="og:description")
    if og_desc and og_desc.get("content"):
        return og_desc["content"].strip()

    meta_desc = soup.find("meta", attrs={"name": "description"})
    if meta_desc and meta_desc.get("content"):
        return meta_desc["content"].strip()

    desc_div = soup.find("div", class_="job-description")
    if desc_div:
        text = desc_div.get_text(separator=" ", strip=True)
        if text:
            return text

    return None


def _extract_tags(soup: BeautifulSoup) -> List[str]:
    """Extract technology tags from /jobs/tag/{tag} links.

    Returns a list of tag slugs found in anchor href attributes.
    """
    tags: list[str] = []
    for link in soup.find_all("a", href=True):
        href = link["href"]
        match = TAG_PATTERN.search(href)
        if match:
            tags.append(match.group(1))
    return tags