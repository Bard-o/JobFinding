"""Sitemap download and parsing for GetOnBoard.

Downloads sitemap.xml.gz, decompresses in-memory, parses with
xml.etree.ElementTree, and filters job URLs.
"""

from __future__ import annotations

import gzip
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import List

import requests
import structlog

from scraper.models import SitemapEntry

logger = structlog.get_logger(__name__)

SITEMAP_URL = "https://www.getonboard.com/sitemap.xml.gz"
JOB_PATH_SEGMENTS = ("/jobs/", "/empleos/")


class SitemapParser:
    """Download, decompress, parse, and filter the GetOnBoard sitemap.

    Usage::

        parser = SitemapParser()
        entries = parser.fetch_sitemap()
        for entry in entries:
            print(entry.url, entry.lastmod)
    """

    def __init__(self, sitemap_url: str = SITEMAP_URL) -> None:
        self.sitemap_url = sitemap_url

    def fetch_sitemap(self) -> List[SitemapEntry]:
        """Download and parse the sitemap, returning job URL entries.

        Downloads the gzipped sitemap, decompresses it in-memory,
        parses the XML, and filters to only /jobs/ and /empleos/ URLs.

        Returns:
            List of SitemapEntry objects for job URLs only.

        Raises:
            requests.HTTPError: If the HTTP request fails (non-200 status).
            ET.ParseError: If the XML content is malformed.
        """
        response = self._download()
        xml_bytes = self._decompress(response.content)
        entries = self._parse(xml_bytes)
        job_entries = self._filter_jobs(entries)

        logger.info(
            "sitemap_parsed",
            total_urls=len(entries),
            job_urls=len(job_entries),
        )

        if not job_entries:
            logger.warning(
                "sitemap_zero_jobs", message="No job URLs discovered from sitemap"
            )

        return job_entries

    def _download(self) -> requests.Response:
        """Download the gzipped sitemap.

        Returns:
            HTTP response with status 200.

        Raises:
            requests.HTTPError: If the response status is not 200.
        """
        logger.info("sitemap_download_start", url=self.sitemap_url)
        response = requests.get(self.sitemap_url, timeout=30)
        response.raise_for_status()
        logger.info(
            "sitemap_download_done",
            status=response.status_code,
            size=len(response.content),
        )
        return response

    @staticmethod
    def _decompress(content: bytes) -> bytes:
        """Decompress gzip content in-memory.

        Args:
            content: Raw gzipped bytes.

        Returns:
            Decompressed XML bytes.
        """
        return gzip.decompress(content)

    @staticmethod
    def _parse(xml_bytes: bytes) -> List[SitemapEntry]:
        """Parse sitemap XML into SitemapEntry objects.

        Handles both <url><loc> (regular sitemaps) and
        <sitemap><loc> (sitemap index) formats.

        Args:
            xml_bytes: Decompressed XML content as bytes.

        Returns:
            All entries found in the sitemap.
        """
        root = ET.fromstring(xml_bytes)
        namespace = _extract_namespace(root.tag)

        entries: list[SitemapEntry] = []
        # Handle both sitemap and urlset root elements
        url_elements = (
            root.findall(f"{namespace}url") if namespace else root.findall("url")
        )

        if not url_elements:
            # Might be a sitemap index — try <sitemap> elements
            url_elements = (
                root.findall(f"{namespace}sitemap")
                if namespace
                else root.findall("sitemap")
            )

        for url_el in url_elements:
            loc_el = url_el.find(f"{namespace}loc") if namespace else url_el.find("loc")
            if loc_el is None or loc_el.text is None:
                continue

            url = loc_el.text.strip()
            lastmod = _parse_lastmod(url_el, namespace)
            entries.append(SitemapEntry(url=url, lastmod=lastmod))

        return entries

    @staticmethod
    def _filter_jobs(entries: List[SitemapEntry]) -> List[SitemapEntry]:
        """Filter sitemap entries to only job URLs.

        A job URL contains '/jobs/' or '/empleos/' in its path.

        Args:
            entries: All sitemap entries.

        Returns:
            Entries whose URL contains a job path segment.
        """
        return [e for e in entries if any(seg in e.url for seg in JOB_PATH_SEGMENTS)]


def _extract_namespace(tag: str) -> str:
    """Extract XML namespace from a tag string.

    Args:
        tag: An element tag like '{http://www.sitemaps.org/schemas/sitemap/0.9}urlset'

    Returns:
        The namespace string including braces, e.g. '{http://...}', or empty string.
    """
    if tag.startswith("{"):
        return tag.split("}", 1)[0] + "}"
    return ""


def _parse_lastmod(url_el: ET.Element, namespace: str) -> object:
    """Parse the lastmod element from a sitemap entry.

    Args:
        url_el: The <url> or <sitemap> XML element.
        namespace: The XML namespace prefix.

    Returns:
        A datetime object if parseable, or None.
    """
    lastmod_el = (
        url_el.find(f"{namespace}lastmod") if namespace else url_el.find("lastmod")
    )
    if lastmod_el is None or lastmod_el.text is None:
        return None

    text = lastmod_el.text.strip()
    for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue

    logger.debug("sitemap_lastmod_unparseable", raw=text)
    return None
