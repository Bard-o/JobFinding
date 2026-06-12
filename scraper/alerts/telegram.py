"""Telegram alert integration for scraper failure notifications.

Sends messages via the Telegram Bot API when critical errors occur
or when zero jobs are scraped.
"""

from __future__ import annotations

import structlog
import requests

from scraper.config import Settings

logger = structlog.get_logger(__name__)

TELEGRAM_API_URL = "https://api.telegram.org/bot{token}/sendMessage"


def send_alert(message: str) -> bool:
    """Send an alert message via Telegram Bot API.

    Sends a POST request to the Telegram Bot API. If the bot token or
    chat ID are not configured, logs a warning and returns False without
    raising an exception.

    Args:
        message: The alert message to send.

    Returns:
        True if the alert was sent successfully, False otherwise.
    """
    try:
        settings = Settings.from_env()
    except ValueError:
        logger.warning(
            "telegram_alert_skipped",
            reason="DATABASE_URL not configured — cannot load settings",
        )
        return False

    if not settings.telegram_bot_token or not settings.telegram_chat_id:
        logger.warning(
            "telegram_alert_skipped",
            reason="TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not set",
        )
        return False

    url = TELEGRAM_API_URL.format(token=settings.telegram_bot_token)
    payload = {
        "chat_id": settings.telegram_chat_id,
        "text": message,
        "parse_mode": "HTML",
    }

    try:
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
        logger.info("telegram_alert_sent", message_length=len(message))
        return True
    except requests.RequestException as e:
        logger.error(
            "telegram_alert_failed",
            error=str(e),
        )
        return False