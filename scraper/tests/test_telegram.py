"""Unit tests for the Telegram alert module."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
import requests

from scraper.alerts.telegram import send_alert


class TestSendAlert:
    """Test send_alert sends messages and handles missing config gracefully."""

    @patch("scraper.alerts.telegram.requests.post")
    @patch("scraper.alerts.telegram.Settings.from_env")
    def test_send_alert_success(self, mock_settings, mock_post) -> None:
        """Alert is sent successfully when config is present."""
        mock_settings.return_value = MagicMock(
            telegram_bot_token="123:ABC",
            telegram_chat_id="987654",
        )
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        result = send_alert("Test alert message")

        assert result is True
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        # URL is the first positional arg, payload is the json kwarg
        assert "123:ABC" in call_args[0][0]  # url is positional
        assert call_args[1]["json"]["chat_id"] == "987654"
        assert call_args[1]["json"]["text"] == "Test alert message"

    @patch("scraper.alerts.telegram.requests.post")
    @patch("scraper.alerts.telegram.Settings.from_env")
    def test_send_alert_missing_token(self, mock_settings, mock_post) -> None:
        """Alert is skipped when TELEGRAM_BOT_TOKEN is not set."""
        mock_settings.return_value = MagicMock(
            telegram_bot_token=None,
            telegram_chat_id="987654",
        )

        result = send_alert("Test message")

        assert result is False
        mock_post.assert_not_called()

    @patch("scraper.alerts.telegram.requests.post")
    @patch("scraper.alerts.telegram.Settings.from_env")
    def test_send_alert_missing_chat_id(self, mock_settings, mock_post) -> None:
        """Alert is skipped when TELEGRAM_CHAT_ID is not set."""
        mock_settings.return_value = MagicMock(
            telegram_bot_token="123:ABC",
            telegram_chat_id=None,
        )

        result = send_alert("Test message")

        assert result is False
        mock_post.assert_not_called()

    @patch("scraper.alerts.telegram.requests.post")
    @patch("scraper.alerts.telegram.Settings.from_env")
    def test_send_alert_config_error(self, mock_settings, mock_post) -> None:
        """Alert is skipped when Settings cannot be loaded (e.g. no DATABASE_URL)."""
        mock_settings.side_effect = ValueError("DATABASE_URL required")

        result = send_alert("Test message")

        assert result is False
        mock_post.assert_not_called()

    @patch("scraper.alerts.telegram.requests.post")
    @patch("scraper.alerts.telegram.Settings.from_env")
    def test_send_alert_network_error(self, mock_settings, mock_post) -> None:
        """Alert returns False on network error, does not raise."""
        mock_settings.return_value = MagicMock(
            telegram_bot_token="123:ABC",
            telegram_chat_id="987654",
        )
        mock_post.side_effect = requests.RequestException("Connection error")

        result = send_alert("Test message")

        assert result is False

    @patch("scraper.alerts.telegram.requests.post")
    @patch("scraper.alerts.telegram.Settings.from_env")
    def test_send_alert_http_error(self, mock_settings, mock_post) -> None:
        """Alert returns False when Telegram returns non-200 status."""
        mock_settings.return_value = MagicMock(
            telegram_bot_token="123:ABC",
            telegram_chat_id="987654",
        )
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = requests.HTTPError("403")
        mock_post.return_value = mock_response

        result = send_alert("Test message")

        assert result is False