"""Unit tests for the GetOnBoard scraper with mocked HTTP responses."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
import requests

from scraper.scrapers.getonboard import (
    BACKOFF_DELAYS,
    USER_AGENTS,
    GetOnBoardScraper,
)

SAMPLE_URL = "https://www.getonboard.com/jobs/programming/react-dev"
SAMPLE_HTML = "<html><body><h1>React Dev</h1></body></html>"


class TestGetOnBoardScraperInit:
    """Test scraper initialization and configuration."""

    def test_default_configuration(self) -> None:
        """Scraper initializes with sensible defaults."""
        scraper = GetOnBoardScraper()
        assert scraper._delay == 1.0
        assert scraper._max_retries == 3
        assert scraper._timeout == 30

    def test_custom_configuration(self) -> None:
        """Scraper accepts custom delay, retries, and timeout."""
        scraper = GetOnBoardScraper(delay=2.0, max_retries=5, timeout=60)
        assert scraper._delay == 2.0
        assert scraper._max_retries == 5
        assert scraper._timeout == 60

    def test_session_is_created(self) -> None:
        """Scraper creates a requests.Session for connection pooling."""
        scraper = GetOnBoardScraper()
        assert isinstance(scraper.session, requests.Session)


class TestUserAgentRotation:
    """Test User-Agent rotation logic."""

    def test_user_agents_cycle(self) -> None:
        """User-Agent rotates through the list based on request count."""
        scraper = GetOnBoardScraper()
        # First 3 requests should cycle through all 3 user agents
        ua0 = scraper._user_agent()
        scraper._request_count = 1
        ua1 = scraper._user_agent()
        scraper._request_count = 2
        ua2 = scraper._user_agent()
        # All should be different
        assert len({ua0, ua1, ua2}) == 3
        # All should be from the known list
        assert ua0 in USER_AGENTS
        assert ua1 in USER_AGENTS
        assert ua2 in USER_AGENTS

    def test_user_agent_wraps_around(self) -> None:
        """After exhausting the list, User-Agent rotation wraps around."""
        scraper = GetOnBoardScraper()
        scraper._request_count = 0
        ua_first = scraper._user_agent()
        scraper._request_count = len(USER_AGENTS)
        ua_wrapped = scraper._user_agent()
        assert ua_first == ua_wrapped


class TestFetchJobDetailHappyPath:
    """Test successful HTTP fetching of job detail pages."""

    @patch("scraper.scrapers.getonboard.time")
    @patch("scraper.scrapers.getonboard.requests.Session.get")
    def test_fetch_returns_html(self, mock_get: MagicMock, mock_time: MagicMock) -> None:
        """Successful fetch returns the HTML content."""
        mock_time.monotonic.return_value = 100.0
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = SAMPLE_HTML
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        scraper = GetOnBoardScraper()
        result = scraper.fetch_job_detail(SAMPLE_URL)

        assert result == SAMPLE_HTML

    @patch("scraper.scrapers.getonboard.time")
    @patch("scraper.scrapers.getonboard.requests.Session.get")
    def test_fetch_sets_user_agent_header(
        self, mock_get: MagicMock, mock_time: MagicMock
    ) -> None:
        """Each request includes a User-Agent header."""
        mock_time.monotonic.return_value = 100.0
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = SAMPLE_HTML
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        scraper = GetOnBoardScraper()
        scraper.fetch_job_detail(SAMPLE_URL)

        call_kwargs = mock_get.call_args
        headers = call_kwargs[1]["headers"]
        assert "User-Agent" in headers
        assert headers["User-Agent"] in USER_AGENTS

    @patch("scraper.scrapers.getonboard.time")
    @patch("scraper.scrapers.getonboard.requests.Session.get")
    def test_fetch_increments_request_count(
        self, mock_get: MagicMock, mock_time: MagicMock
    ) -> None:
        """Each successful fetch increments the request counter."""
        mock_time.monotonic.return_value = 100.0
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = SAMPLE_HTML
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        scraper = GetOnBoardScraper()
        assert scraper._request_count == 0

        scraper.fetch_job_detail(SAMPLE_URL)
        assert scraper._request_count == 1

        scraper.fetch_job_detail(SAMPLE_URL)
        assert scraper._request_count == 2


class TestFetchJobDetailRateLimiting:
    """Test rate limiting behavior between requests."""

    @patch("scraper.scrapers.getonboard.time")
    @patch("scraper.scrapers.getonboard.requests.Session.get")
    def test_rate_limit_sleep_when_needed(
        self, mock_get: MagicMock, mock_time: MagicMock
    ) -> None:
        """When less than 1 second since last request, sleep is called for the remainder."""
        # _enforce_rate_limit checks: elapsed = monotonic() - _last_request_time
        # If _last_request_time = 99.2 and monotonic() = 100.0, elapsed = 0.8
        # delay = 1.0, sleep_time = 1.0 - 0.8 = 0.2
        mock_time.monotonic.side_effect = [100.0, 100.0]
        mock_time.sleep = MagicMock()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = SAMPLE_HTML
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        scraper = GetOnBoardScraper(delay=1.0)
        scraper._last_request_time = 99.2  # 0.8s ago

        scraper.fetch_job_detail(SAMPLE_URL)

        # time.sleep should have been called (rate limiting enforced)
        mock_time.sleep.assert_called()
        # The sleep time should be ~0.2s (1.0 - 0.8s elapsed)
        sleep_call_args = mock_time.sleep.call_args[0][0]
        assert 0.18 <= sleep_call_args <= 0.22


class TestFetchJobDetailRetryOn429:
    """Test exponential backoff and retry behavior on HTTP 429."""

    @patch("scraper.scrapers.getonboard.time")
    @patch("scraper.scrapers.getonboard.requests.Session.get")
    def test_429_retries_with_backoff(
        self, mock_get: MagicMock, mock_time: MagicMock
    ) -> None:
        """On 429, retries with exponential backoff delays."""
        mock_time.monotonic.return_value = 100.0
        mock_time.sleep = MagicMock()

        # First call returns 429, second returns 200
        response_429 = MagicMock()
        response_429.status_code = 429
        response_429.raise_for_status = MagicMock()

        response_200 = MagicMock()
        response_200.status_code = 200
        response_200.text = SAMPLE_HTML
        response_200.raise_for_status = MagicMock()

        mock_get.side_effect = [response_429, response_200]

        scraper = GetOnBoardScraper()
        result = scraper.fetch_job_detail(SAMPLE_URL)

        assert result == SAMPLE_HTML

        # Should have slept with backoff delay 2s (first attempt)
        sleep_calls = [call[0][0] for call in mock_time.sleep.call_args_list]
        assert BACKOFF_DELAYS[0] in sleep_calls

    @patch("scraper.scrapers.getonboard.time")
    @patch("scraper.scrapers.getonboard.requests.Session.get")
    def test_429_exhausted_retries_raises(
        self, mock_get: MagicMock, mock_time: MagicMock
    ) -> None:
        """After exhausting max retries on 429, raises HTTPError."""
        mock_time.monotonic.return_value = 100.0
        mock_time.sleep = MagicMock()

        response_429 = MagicMock()
        response_429.status_code = 429
        response_429.raise_for_status = MagicMock(
            side_effect=requests.HTTPError("429 Too Many Requests")
        )

        # All attempts return 429
        mock_get.return_value = response_429

        scraper = GetOnBoardScraper(max_retries=3)
        with pytest.raises(requests.HTTPError):
            scraper.fetch_job_detail(SAMPLE_URL)

    @patch("scraper.scrapers.getonboard.time")
    @patch("scraper.scrapers.getonboard.requests.Session.get")
    def test_backoff_delays_increase(
        self, mock_get: MagicMock, mock_time: MagicMock
    ) -> None:
        """Backoff delays follow the exponential sequence 2, 4, 8."""
        mock_time.monotonic.return_value = 100.0
        mock_time.sleep = MagicMock()

        # First two calls return 429, third returns 200
        response_429 = MagicMock()
        response_429.status_code = 429
        response_429.raise_for_status = MagicMock()

        response_200 = MagicMock()
        response_200.status_code = 200
        response_200.text = SAMPLE_HTML
        response_200.raise_for_status = MagicMock()

        mock_get.side_effect = [response_429, response_429, response_200]

        scraper = GetOnBoardScraper()
        scraper.fetch_job_detail(SAMPLE_URL)

        # Extract sleep calls that correspond to backoff (not rate-limit)
        sleep_calls = [call[0][0] for call in mock_time.sleep.call_args_list]
        # The backoff delays should be BACKOFF_DELAYS[0]=2 and BACKOFF_DELAYS[1]=4
        assert BACKOFF_DELAYS[0] in sleep_calls
        assert BACKOFF_DELAYS[1] in sleep_calls


class TestFetchJobDetailNetworkErrors:
    """Test handling of network errors."""

    @patch("scraper.scrapers.getonboard.time")
    @patch("scraper.scrapers.getonboard.requests.Session.get")
    def test_connection_error_raises(
        self, mock_get: MagicMock, mock_time: MagicMock
    ) -> None:
        """ConnectionError is raised after exhausting retries."""
        mock_time.monotonic.return_value = 100.0
        mock_time.sleep = MagicMock()
        mock_get.side_effect = requests.ConnectionError("Network unreachable")

        scraper = GetOnBoardScraper()
        with pytest.raises(requests.ConnectionError):
            scraper.fetch_job_detail(SAMPLE_URL)

    @patch("scraper.scrapers.getonboard.time")
    @patch("scraper.scrapers.getonboard.requests.Session.get")
    def test_http_error_404_raises(
        self, mock_get: MagicMock, mock_time: MagicMock
    ) -> None:
        """Non-429 HTTP errors are raised immediately."""
        mock_time.monotonic.return_value = 100.0
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = requests.HTTPError("404 Not Found")

        mock_get.return_value = mock_response

        scraper = GetOnBoardScraper()
        with pytest.raises(requests.HTTPError):
            scraper.fetch_job_detail(SAMPLE_URL)

    @patch("scraper.scrapers.getonboard.time.monotonic")
    @patch("scraper.scrapers.getonboard.requests.Session.get")
    def test_timeout_error_raises(
        self, mock_get: MagicMock, mock_monotonic: MagicMock
    ) -> None:
        """Timeout errors are raised."""
        mock_monotonic.return_value = 100.0
        mock_get.side_effect = requests.Timeout("Connection timed out")

        scraper = GetOnBoardScraper()
        with pytest.raises(requests.Timeout):
            scraper.fetch_job_detail(SAMPLE_URL)