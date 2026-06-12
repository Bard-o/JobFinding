"""Scrapers package — HTTP fetching logic for job sources."""

from scraper.scrapers.getonboard import GetOnBoardScraper
from scraper.scrapers.remotive import RemotiveScraper

__all__ = ["GetOnBoardScraper", "RemotiveScraper"]
