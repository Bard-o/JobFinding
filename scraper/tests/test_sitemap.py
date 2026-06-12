"""Unit tests for scraper.sitemap module."""

from __future__ import annotations

import gzip
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from scraper.models import SitemapEntry
from scraper.sitemap import SitemapParser


class TestSitemapParserFiltering:
    """Test that SitemapParser correctly filters job URLs."""

    def test_filter_keeps_jobs_urls(self) -> None:
        """Only URLs containing /jobs/ are kept."""
        entries = [
            SitemapEntry(url="https://www.getonboard.com/jobs/dev", lastmod=None),
            SitemapEntry(
                url="https://www.getonboard.com/categories/remote", lastmod=None
            ),
            SitemapEntry(url="https://www.getonboard.com/companies/acme", lastmod=None),
        ]
        result = SitemapParser._filter_jobs(entries)
        assert len(result) == 1
        assert "/jobs/" in result[0].url

    def test_filter_keeps_empleos_urls(self) -> None:
        """URLs containing /empleos/ are also kept (Spanish variant)."""
        entries = [
            SitemapEntry(url="https://www.getonboard.com/empleos/dev", lastmod=None),
            SitemapEntry(url="https://www.getonboard.com/about", lastmod=None),
        ]
        result = SitemapParser._filter_jobs(entries)
        assert len(result) == 1
        assert "/empleos/" in result[0].url

    def test_filter_empty_list(self) -> None:
        """Empty input returns empty output."""
        result = SitemapParser._filter_jobs([])
        assert result == []

    def test_filter_no_job_urls(self) -> None:
        """If no URLs match job patterns, result is empty."""
        entries = [
            SitemapEntry(
                url="https://www.getonboard.com/categories/remote", lastmod=None
            ),
            SitemapEntry(url="https://www.getonboard.com/companies/acme", lastmod=None),
        ]
        result = SitemapParser._filter_jobs(entries)
        assert result == []


class TestSitemapParserDecompress:
    """Test in-memory gzip decompression."""

    def test_decompress_valid_gzip(self) -> None:
        """Decompresses a valid gzip byte stream."""
        original = b"<urlset></urlset>"
        compressed = gzip.compress(original)
        result = SitemapParser._decompress(compressed)
        assert result == original


class TestSitemapParserParse:
    """Test XML parsing into SitemapEntry objects."""

    def test_parse_urls_with_namespace(self, sample_sitemap_xml: str) -> None:
        """Parses a sitemap with xmlns namespace into entries."""
        result = SitemapParser._parse(sample_sitemap_xml.encode("utf-8"))
        assert len(result) == 6  # all 6 URLs in fixture

    def test_parse_extracts_url_and_lastmod(self, sample_sitemap_xml: str) -> None:
        """Each entry has url and lastmod correctly extracted."""
        result = SitemapParser._parse(sample_sitemap_xml.encode("utf-8"))
        # First entry: /jobs/ URL with date-only lastmod
        assert result[0].url == "https://www.getonboard.com/jobs/programming/react-dev"
        assert result[0].lastmod is not None

    def test_parse_entry_without_lastmod(self, sample_sitemap_xml: str) -> None:
        """Entries without lastmod get None."""
        result = SitemapParser._parse(sample_sitemap_xml.encode("utf-8"))
        # The /categories/ URL has no lastmod
        category_entry = [e for e in result if "/categories/" in e.url][0]
        assert category_entry.lastmod is None

    def test_parse_empty_urlset(self) -> None:
        """Empty urlset returns empty list."""
        xml = b'<?xml version="1.0"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"></urlset>'
        result = SitemapParser._parse(xml)
        assert result == []

    def test_parse_sitemap_index(self, sitemap_index_xml: str) -> None:
        """Sitemap index format (<sitemap> elements) is handled."""
        result = SitemapParser._parse(sitemap_index_xml.encode("utf-8"))
        assert len(result) == 1
        assert "sitemap-jobs.xml.gz" in result[0].url


class TestSitemapParserFetchSitemap:
    """Integration-style tests for fetch_sitemap with mocked HTTP."""

    @patch("scraper.sitemap.requests.get")
    def test_fetch_sitemap_returns_job_urls(
        self, mock_get: MagicMock, sample_sitemap_gz: bytes
    ) -> None:
        """End-to-end: download gzip → decompress → parse → filter → only /jobs/ URLs."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = sample_sitemap_gz
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        parser = SitemapParser()
        result = parser.fetch_sitemap()

        # sample_sitemap_xml has 4 job URLs (3 /jobs/, 1 /empleos/)
        assert len(result) == 4
        assert all("/jobs/" in e.url or "/empleos/" in e.url for e in result)

    @patch("scraper.sitemap.requests.get")
    def test_fetch_sitemap_empty_jobs(
        self, mock_get: MagicMock, empty_sitemap_gz: bytes
    ) -> None:
        """Sitemap with no job URLs returns empty list and logs warning."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = empty_sitemap_gz
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        parser = SitemapParser()
        result = parser.fetch_sitemap()

        assert result == []

    @patch("scraper.sitemap.requests.get")
    def test_fetch_sitemap_custom_url(self, mock_get: MagicMock) -> None:
        """SitemapParser uses the custom URL when provided."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = gzip.compress(
            b'<?xml version="1.0"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"><url><loc>https://example.com/jobs/1</loc></url></urlset>'
        )
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        custom_url = "https://example.com/sitemap.xml.gz"
        parser = SitemapParser(sitemap_url=custom_url)
        parser.fetch_sitemap()

        mock_get.assert_called_once_with(custom_url, timeout=30)

    @patch("scraper.sitemap.requests.get")
    def test_fetch_sitemap_http_error(self, mock_get: MagicMock) -> None:
        """HTTP errors are raised (not swallowed)."""
        mock_get.side_effect = ConnectionError("Network unreachable")

        parser = SitemapParser()
        with pytest.raises(ConnectionError, match="Network unreachable"):
            parser.fetch_sitemap()
