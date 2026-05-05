"""Type definitions for crawler return values."""
from typing import TypedDict


class NewsCrawlResult(TypedDict):
    """Return type for CafeFCrawler.crawl_all_tickers()."""
    success: int
    failed: int
    total_articles: int
    failed_symbols: list[str]


class RumorCrawlResult(TypedDict):
    """Return type for FireantCrawler.crawl_watchlist_tickers()."""
    success: int
    failed: int
    total_posts: int
    failed_symbols: list[str]
