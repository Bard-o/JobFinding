"""Pytest fixtures for scraper tests."""

from __future__ import annotations

import gzip
from datetime import datetime, timezone
from typing import Generator

import pytest


@pytest.fixture
def sample_sitemap_xml() -> str:
    """A minimal valid sitemap with mixed URL types.

    Includes /jobs/, /empleos/, and non-job URLs to test filtering.
    """
    return """\
<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url>
    <loc>https://www.getonboard.com/jobs/programming/react-dev</loc>
    <lastmod>2024-01-15</lastmod>
  </url>
  <url>
    <loc>https://www.getonboard.com/jobs/design/ux-designer</loc>
    <lastmod>2024-01-14T10:30:00+00:00</lastmod>
  </url>
  <url>
    <loc>https://www.getonboard.com/empleos/programming/python-dev</loc>
    <lastmod>2024-01-13T08:00:00</lastmod>
  </url>
  <url>
    <loc>https://www.getonboard.com/companies/acme-corp</loc>
    <lastmod>2024-01-10</lastmod>
  </url>
  <url>
    <loc>https://www.getonboard.com/categories/remote</loc>
  </url>
  <url>
    <loc>https://www.getonboard.com/jobs/devops/site-reliability</loc>
    <lastmod>2024-01-12</lastmod>
  </url>
</urlset>
"""


@pytest.fixture
def sample_sitemap_gz(sample_sitemap_xml: str) -> bytes:
    """Gzipped version of sample_sitemap_xml, as returned by the real endpoint."""
    return gzip.compress(sample_sitemap_xml.encode("utf-8"))


@pytest.fixture
def empty_sitemap_xml() -> str:
    """A sitemap with no job URLs (only non-job entries)."""
    return """\
<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url>
    <loc>https://www.getonboard.com/categories/remote</loc>
  </url>
  <url>
    <loc>https://www.getonboard.com/companies/test-corp</loc>
    <lastmod>2024-01-01</lastmod>
  </url>
</urlset>
"""


@pytest.fixture
def empty_sitemap_gz(empty_sitemap_xml: str) -> bytes:
    """Gzipped version of empty_sitemap_xml."""
    return gzip.compress(empty_sitemap_xml.encode("utf-8"))


@pytest.fixture
def sitemap_index_xml() -> str:
    """A sitemap index file (not a urlset) to test index handling."""
    return """\
<?xml version="1.0" encoding="UTF-8"?>
<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <sitemap>
    <loc>https://www.getonboard.com/sitemap-jobs.xml.gz</loc>
    <lastmod>2024-01-15</lastmod>
  </sitemap>
</sitemapindex>
"""


@pytest.fixture
def sitemap_index_gz(sitemap_index_xml: str) -> bytes:
    """Gzipped version of sitemap_index_xml."""
    return gzip.compress(sitemap_index_xml.encode("utf-8"))
