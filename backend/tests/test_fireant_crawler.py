"""Tests for Fireant community post crawler — parsing, filtering, dedup, cleanup."""
import pytest
import httpx
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from app.crawlers.fireant_crawler import FireantCrawler, _is_retryable


# --- Sample Fireant API JSON ---

SAMPLE_POSTS = [
    {
        "postID": 12345,
        "content": "Tin t&#7913;c VNM s&#7869; t&#259;ng gi&#225; m&#7841;nh trong tu&#7847;n t&#7899;i",
        "date": "2025-07-21T14:30:00+07:00",
        "sentiment": 1,
        "totalLikes": 5,
        "totalReplies": 2,
        "user": {"name": "trader123", "isAuthentic": True},
        "taggedSymbols": [{"symbol": "VNM"}],
    },
    {
        "postID": 12346,
        "content": "ok",  # < 20 chars — should be filtered
        "date": "2025-07-21T15:00:00+07:00",
        "sentiment": 0,
        "totalLikes": 0,
        "totalReplies": 0,
        "user": {"name": "user2", "isAuthentic": False},
        "taggedSymbols": [],
    },
]


def _make_crawler(session=None):
    """Create a FireantCrawler instance without real DB for unit tests."""
    crawler = FireantCrawler.__new__(FireantCrawler)
    crawler.session = session or AsyncMock()
    crawler.delay = 0
    crawler.post_limit = 20
    crawler.retention_days = 30
    crawler.headers = {"Authorization": "Bearer test", "User-Agent": "test"}
    return crawler


class TestParsePostsExtraction:
    """Test _parse_posts field extraction from Fireant JSON."""

    def test_parse_posts_extracts_all_fields(self):
        """_parse_posts must extract postID, content, author, sentiment, likes, replies, posted_at."""
        crawler = _make_crawler()
        result = crawler._parse_posts(SAMPLE_POSTS)

        assert len(result) == 1  # second post filtered (< 20 chars)
        post = result[0]
        assert post["post_id"] == 12345
        assert post["author_name"] == "trader123"
        assert post["is_authentic"] is True
        assert post["total_likes"] == 5
        assert post["total_replies"] == 2
        assert post["fireant_sentiment"] == 1
        assert isinstance(post["posted_at"], datetime)

    def test_parse_posts_html_unescape(self):
        """_parse_posts must apply html.unescape() — HTML entities become Vietnamese chars."""
        crawler = _make_crawler()
        result = crawler._parse_posts(SAMPLE_POSTS)

        # &#7913; = ứ, &#7869; = ẽ, &#259; = ă, &#225; = á, etc.
        content = result[0]["content"]
        assert "&#" not in content  # No raw HTML entities remaining
        assert "tức" in content or "á" in content  # Vietnamese chars present

    def test_parse_posts_filters_short_content(self):
        """_parse_posts must filter out posts with content < 20 characters."""
        crawler = _make_crawler()
        short_posts = [
            {
                "postID": 999,
                "content": "short",
                "date": "2025-07-21T10:00:00+07:00",
                "sentiment": 0,
                "totalLikes": 0,
                "totalReplies": 0,
                "user": {"name": "user1", "isAuthentic": False},
            },
        ]
        result = crawler._parse_posts(short_posts)
        assert len(result) == 0

    def test_parse_posts_missing_user_field(self):
        """_parse_posts must handle missing user field — default to 'Unknown' and False."""
        crawler = _make_crawler()
        posts = [
            {
                "postID": 999,
                "content": "x" * 25,  # > 20 chars
                "date": "2025-07-21T10:00:00+07:00",
                "sentiment": 0,
                "totalLikes": 0,
                "totalReplies": 0,
                # No "user" field
            },
        ]
        result = crawler._parse_posts(posts)
        assert len(result) == 1
        assert result[0]["author_name"] == "Unknown"
        assert result[0]["is_authentic"] is False

    def test_parse_posts_empty_input(self):
        """_parse_posts must return empty list for empty input."""
        crawler = _make_crawler()
        assert crawler._parse_posts([]) == []


class TestStorePosts:
    """Test _store_posts DB insertion logic."""

    @pytest.mark.asyncio
    async def test_store_posts_inserts_new(self):
        """_store_posts must insert new post and return count 1."""
        session = AsyncMock()
        mock_result = MagicMock()
        mock_result.rowcount = 1
        session.execute = AsyncMock(return_value=mock_result)

        crawler = _make_crawler(session)
        posts = [
            {
                "post_id": 12345,
                "content": "Test content for storage",
                "author_name": "trader",
                "is_authentic": True,
                "total_likes": 5,
                "total_replies": 2,
                "fireant_sentiment": 1,
                "posted_at": datetime(2025, 7, 21, 14, 30, tzinfo=timezone.utc),
            },
        ]
        stored = await crawler._store_posts(1, posts)
        assert stored == 1
        session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_store_posts_duplicate_returns_zero(self):
        """_store_posts with duplicate post_id returns 0 (ON CONFLICT DO NOTHING)."""
        session = AsyncMock()
        mock_result = MagicMock()
        mock_result.rowcount = 0  # Conflict — not inserted
        session.execute = AsyncMock(return_value=mock_result)

        crawler = _make_crawler(session)
        posts = [
            {
                "post_id": 12345,
                "content": "Duplicate content for testing",
                "author_name": "trader",
                "is_authentic": False,
                "total_likes": 0,
                "total_replies": 0,
                "fireant_sentiment": 0,
                "posted_at": datetime(2025, 7, 21, 14, 30, tzinfo=timezone.utc),
            },
        ]
        stored = await crawler._store_posts(1, posts)
        assert stored == 0

    @pytest.mark.asyncio
    async def test_store_posts_empty_returns_zero(self):
        """_store_posts with empty list returns 0 without DB call."""
        session = AsyncMock()
        crawler = _make_crawler(session)
        stored = await crawler._store_posts(1, [])
        assert stored == 0
        session.execute.assert_not_called()


class TestCleanupOldPosts:
    """Test _cleanup_old_posts retention logic."""

    @pytest.mark.asyncio
    async def test_cleanup_old_posts_executes_delete(self):
        """_cleanup_old_posts must execute DELETE for posts older than retention_days."""
        session = AsyncMock()
        mock_result = MagicMock()
        mock_result.rowcount = 5
        session.execute = AsyncMock(return_value=mock_result)

        crawler = _make_crawler(session)
        await crawler._cleanup_old_posts()

        session.execute.assert_called_once()


class TestCrawlWatchlistTickers:
    """Test crawl_watchlist_tickers orchestration."""

    @pytest.mark.asyncio
    async def test_crawl_returns_rumor_crawl_result_shape(self):
        """crawl_watchlist_tickers must return dict with success, failed, total_posts, failed_symbols."""
        session = AsyncMock()

        # Mock watchlist query returning empty → should return zeros
        mock_query_result = MagicMock()
        mock_query_result.fetchall.return_value = []
        session.execute = AsyncMock(return_value=mock_query_result)

        crawler = _make_crawler(session)
        result = await crawler.crawl_watchlist_tickers()

        assert "success" in result
        assert "failed" in result
        assert "total_posts" in result
        assert "failed_symbols" in result
        assert result["success"] == 0
        assert result["failed"] == 0
        assert result["total_posts"] == 0
        assert result["failed_symbols"] == []


class TestIsRetryable:
    """Test _is_retryable helper for tenacity retry logic."""

    def test_timeout_is_retryable(self):
        assert _is_retryable(httpx.TimeoutException("timeout")) is True

    def test_connect_error_is_retryable(self):
        assert _is_retryable(httpx.ConnectError("connection failed")) is True

    def test_server_error_is_retryable(self):
        request = httpx.Request("GET", "https://example.com")
        response = httpx.Response(500, request=request)
        exc = httpx.HTTPStatusError("server error", request=request, response=response)
        assert _is_retryable(exc) is True

    def test_client_error_not_retryable(self):
        request = httpx.Request("GET", "https://example.com")
        response = httpx.Response(404, request=request)
        exc = httpx.HTTPStatusError("not found", request=request, response=response)
        assert _is_retryable(exc) is False

    def test_value_error_not_retryable(self):
        assert _is_retryable(ValueError("bad value")) is False
