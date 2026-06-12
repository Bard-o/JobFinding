"""GetOnBoard HTTP scraper with rate limiting and retry logic.

Uses requests.Session for connection pooling, User-Agent rotation,
and exponential backoff on 429 responses.
"""

from __future__ import annotations

import time
from typing import List

import requests
import structlog

logger = structlog.get_logger(__name__)

# User-Agent strings for rotation — mimics common browsers
USER_AGENTS: List[str] = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
]

# Exponential backoff delays for 429 responses (seconds)
BACKOFF_DELAYS: List[int] = [2, 4, 8]

DEFAULT_REQUEST_TIMEOUT: int = 30


class GetOnBoardScraper:
    """Fetches job detail pages from GetOnBoard with rate limiting and retries.

    Uses a ``requests.Session`` for connection pooling and rotates User-Agent
    headers across requests. Enforces a minimum 1-second delay between
    consecutive requests and applies exponential backoff on HTTP 429
    (Too Many Requests) responses.

    Usage::

        scraper = GetOnBoardScraper()
        html = scraper.fetch_job_detail("https://www.getonboard.com/jobs/programming/react-dev")
    """

    def __init__(
        self,
        delay: float = 1.0,
        max_retries: int = 3,
        timeout: int = DEFAULT_REQUEST_TIMEOUT,
    ) -> None:
        """Initialize the scraper.

        Args:
            delay: Minimum seconds between requests (default: 1.0).
            max_retries: Maximum number of retry attempts on 429 (default: 3).
            timeout: HTTP request timeout in seconds (default: 30).
        """
        self._session = requests.Session()
        self._delay = delay
        self._max_retries = max_retries
        self._timeout = timeout
        self._request_count: int = 0
        self._last_request_time: float = 0.0

    @property
    def session(self) -> requests.Session:
        """The underlying requests.Session for connection pooling."""
        return self._session

    def _user_agent(self) -> str:
        """Return the next User-Agent in the rotation.

        Cycles through USER_AGENTS based on the current request count.
        """
        return USER_AGENTS[self._request_count % len(USER_AGENTS)]

    def _enforce_rate_limit(self) -> None:
        """Wait if not enough time has elapsed since the last request.

        Ensures at least ``self._delay`` seconds pass between requests.
        """
        if self._last_request_time > 0:
            elapsed = time.monotonic() - self._last_request_time
            if elapsed < self._delay:
                sleep_time = self._delay - elapsed
                logger.debug("rate_limit_sleep", sleep_seconds=round(sleep_time, 2))
                time.sleep(sleep_time)

    def fetch_job_detail(self, url: str) -> str:
        """Fetch the HTML content of a job detail page.

        Applies rate limiting between requests, rotates User-Agent headers,
        and retries with exponential backoff on HTTP 429 responses.

        Args:
            url: The full URL of the GetOnBoard job detail page.

        Returns:
            The HTML content of the page as a string.

        Raises:
            requests.HTTPError: If the response status is not 200 after
                exhausting retries.
            requests.RequestException: If a network error occurs.
        """
        self._enforce_rate_limit()

        headers = {"User-Agent": self._user_agent()}

        for attempt in range(self._max_retries + 1):
            try:
                logger.info(
                    "fetch_job_detail",
                    url=url,
                    attempt=attempt + 1,
                    max_retries=self._max_retries,
                )

                response = self._session.get(
                    url, headers=headers, timeout=self._timeout
                )
                self._request_count += 1
                self._last_request_time = time.monotonic()

                if response.status_code == 429:
                    if attempt < self._max_retries:
                        backoff = BACKOFF_DELAYS[attempt]
                        logger.warning(
                            "rate_limited_429",
                            url=url,
                            attempt=attempt + 1,
                            backoff_seconds=backoff,
                        )
                        time.sleep(backoff)
                        headers = {"User-Agent": self._user_agent()}
                        continue
                    else:
                        logger.error(
                            "rate_limited_exhausted",
                            url=url,
                            attempts=attempt + 1,
                        )
                        response.raise_for_status()

                response.raise_for_status()

                logger.info(
                    "fetch_job_detail_success",
                    url=url,
                    status=response.status_code,
                    size=len(response.text),
                )
                return response.text

            except requests.RequestException as e:
                if attempt < self._max_retries and not isinstance(
                    e, requests.HTTPError
                ):
                    logger.warning(
                        "request_error_retrying",
                        url=url,
                        attempt=attempt + 1,
                        error=str(e),
                    )
                    time.sleep(BACKOFF_DELAYS[attempt])
                    continue
                raise

        # Should not reach here, but satisfy type checker
        raise requests.RequestException("Unexpected state in fetch_job_detail")