"""Configuration loaded from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass
class Settings:
    """Application settings loaded from environment variables.

    Attributes:
        database_url: PostgreSQL connection string (required).
        telegram_bot_token: Bot token for Telegram alerts (optional).
        telegram_chat_id: Chat ID for Telegram alerts (optional).
        source_id: Source ID in the sources table (default: 1 = GetOnBoard).
    """

    database_url: str
    telegram_bot_token: str | None
    telegram_chat_id: str | None
    source_id: int = 1  # GetOnBoard in seeds/sources.sql

    @classmethod
    def from_env(cls) -> Settings:
        """Load settings from environment variables.

        Raises:
            ValueError: If DATABASE_URL is not set.
        """
        database_url = os.environ.get("DATABASE_URL", "")
        if not database_url:
            raise ValueError("DATABASE_URL environment variable is required")

        return cls(
            database_url=database_url,
            telegram_bot_token=os.environ.get("TELEGRAM_BOT_TOKEN") or None,
            telegram_chat_id=os.environ.get("TELEGRAM_CHAT_ID") or None,
        )
