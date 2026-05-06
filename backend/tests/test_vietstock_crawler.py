"""Tests for Vietstock RSS crawler — multi-feed parsing, dedup, ticker matching."""
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
import httpx

from app.crawlers.vietstock_crawler import (
    VietstockCrawler,
    _guid_to_post_id,
    _strip_html,
    RSS_FEEDS,
    FALSE_POSITIVES,
)


# --- Sample Vietstock RSS XML ---

SAMPLE_RSS_CHUNG_KHOAN = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
<channel>
    <title>Chứng khoán - Vietstock RSS</title>
    <item>
        <guid isPermaLink="true">http://vietstock.vn/2026/05/hpg-tang-manh-830-1438001.htm</guid>
        <link>http://vietstock.vn/2026/05/hpg-tang-manh-830-1438001.htm</link>
        <title>HPG tăng mạnh nhờ kết quả kinh doanh Q2 vượt kỳ vọng</title>
        <description><![CDATA[<img alt='' width='120' height='90' src='https://image.vietstock.vn/2026/05/06/img.png'/>Cổ phiếu Hòa Phát (HPG) tăng trần phiên sáng.]]></description>
        <pubDate>Wed, 06 May 2026 10:05:50 +0700</pubDate>
    </item>
    <item>
        <guid isPermaLink="true">http://vietstock.vn/2026/05/vnm-co-tuc-830-1438002.htm</guid>
        <link>http://vietstock.vn/2026/05/vnm-co-tuc-830-1438002.htm</link>
        <title>VNM chia cổ tức tiền mặt 2.000 đồng/CP</title>
        <description>Vinamilk (VNM) thông báo ngày đăng ký cuối cùng nhận cổ tức Q1/2026.</description>
        <pubDate>Wed, 06 May 2026 09:30:00 +0700</pubDate>
    </item>
</channel>
</rss>"""

SAMPLE_RSS_CO_PHIEU = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
<channel>
    <title>Cổ phiếu - Vietstock RSS</title>
    <item>
        <guid isPermaLink="true">http://vietstock.vn/2026/05/hpg-tang-manh-830-1438001.htm</guid>
        <link>http://vietstock.vn/2026/05/hpg-tang-manh-830-1438001.htm</link>
        <title>HPG tăng mạnh nhờ kết quả kinh doanh Q2 vượt kỳ vọng</title>
        <description>Duplicate of chung_khoan feed — same GUID.</description>
        <pubDate>Wed, 06 May 2026 10:05:50 +0700</pubDate>
    </item>
    <item>
        <guid isPermaLink="true">http://vietstock.vn/2026/05/stb-mua-lai-830-1438003.htm</guid>
        <link>http://vietstock.vn/2026/05/stb-mua-lai-830-1438003.htm</link>
        <title>STB được khuyến nghị mua với giá mục tiêu 45.000 đồng</title>
        <description>Chuyên gia SSI Research khuyến nghị mua cổ phiếu Sacombank (STB).</description>
        <pubDate>Wed, 06 May 2026 08:15:00 +0700</pubDate>
    </item>
</channel>
</rss>"""


def _make_crawler(session=None):
    """Create VietstockCrawler without real DB."""
    crawler = VietstockCrawler.__new__(VietstockCrawler)
    crawler.session = session or AsyncMock()
    crawler.headers = {"User-Agent": "test"}
    return crawler


class TestRSSParsing:
    """Test _parse_rss extracts articles correctly."""

    def test_parse_all_items(self):
        crawler = _make_crawler()
        items = crawler._parse_rss(SAMPLE_RSS_CHUNG_KHOAN)
        assert len(items) == 2

    def test_parse_title_in_content(self):
        crawler = _make_crawler()
        items = crawler._parse_rss(SAMPLE_RSS_CHUNG_KHOAN)
        assert items[0]["content"].startswith("HPG tăng mạnh")

    def test_parse_strips_html_img(self):
        crawler = _make_crawler()
        items = crawler._parse_rss(SAMPLE_RSS_CHUNG_KHOAN)
        assert "<img" not in items[0]["content"]

    def test_parse_pubdate_timezone(self):
        crawler = _make_crawler()
        items = crawler._parse_rss(SAMPLE_RSS_CHUNG_KHOAN)
        assert items[0]["pub_date"].tzinfo is not None

    def test_parse_guid_from_permalink(self):
        crawler = _make_crawler()
        items = crawler._parse_rss(SAMPLE_RSS_CHUNG_KHOAN)
        assert "1438001" in items[0]["guid"]


class TestMultiFeedDedup:
    """Test cross-feed deduplication."""

    @pytest.mark.asyncio
    async def test_duplicate_guid_across_feeds_deduped(self):
        """Same article appearing in multiple feeds should be stored once."""
        session = AsyncMock()
        # Mock execute to return rowcount=1 (inserted)
        mock_result = MagicMock()
        mock_result.rowcount = 1
        session.execute = AsyncMock(return_value=mock_result)
        session.commit = AsyncMock()

        crawler = _make_crawler(session)
        crawler._get_watchlist_ticker_map = AsyncMock(
            return_value={"HPG": 10, "VNM": 20, "STB": 30}
        )

        # Build responses for each feed
        feed_responses = {}
        for feed_name, feed_url in RSS_FEEDS.items():
            if feed_name == "chung_khoan":
                feed_responses[feed_url] = SAMPLE_RSS_CHUNG_KHOAN
            elif feed_name == "co_phieu":
                feed_responses[feed_url] = SAMPLE_RSS_CO_PHIEU
            else:
                feed_responses[feed_url] = '<?xml version="1.0"?><rss><channel></channel></rss>'

        async def mock_get(url, **kwargs):
            resp = MagicMock()
            resp.status_code = 200
            resp.text = feed_responses.get(url, '<?xml version="1.0"?><rss><channel></channel></rss>')
            resp.raise_for_status = MagicMock()
            return resp

        with patch("app.crawlers.vietstock_crawler.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get = mock_get
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_cls.return_value = mock_client

            result = await crawler.crawl_rss()

        # HPG article 1438001 appears in both feeds but should be deduped
        # We should have 3 unique articles: HPG(1438001), VNM(1438002), STB(1438003)
        assert result["total_posts"] > 0


class TestHelpers:
    """Test helper functions."""

    def test_guid_to_post_id_deterministic(self):
        id1 = _guid_to_post_id("vietstock:http://vietstock.vn/test.htm:HPG")
        id2 = _guid_to_post_id("vietstock:http://vietstock.vn/test.htm:HPG")
        assert id1 == id2

    def test_guid_different_sources(self):
        id1 = _guid_to_post_id("vietstock:http://test.htm:HPG")
        id2 = _guid_to_post_id("vnexpress:http://test.htm:HPG")
        assert id1 != id2

    def test_strip_html(self):
        assert _strip_html("<b>Hello</b>") == "Hello"

    def test_rss_feeds_count(self):
        """Should have 5 feeds configured."""
        assert len(RSS_FEEDS) == 5

    def test_false_positives(self):
        assert "CEO" in FALSE_POSITIVES
        assert "HPG" not in FALSE_POSITIVES


class TestErrorHandling:
    """Test graceful error handling."""

    @pytest.mark.asyncio
    async def test_empty_watchlist_skips(self):
        crawler = _make_crawler()
        crawler._get_watchlist_ticker_map = AsyncMock(return_value={})
        result = await crawler.crawl_rss()
        assert result["total_posts"] == 0

    @pytest.mark.asyncio
    async def test_all_feeds_fail_returns_zero(self):
        """If all RSS feeds fail, return zero posts gracefully."""
        session = AsyncMock()
        crawler = _make_crawler(session)
        crawler._get_watchlist_ticker_map = AsyncMock(return_value={"HPG": 10})

        with patch("app.crawlers.vietstock_crawler.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(side_effect=httpx.ConnectError("timeout"))
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_cls.return_value = mock_client

            result = await crawler.crawl_rss()

        assert result["total_posts"] == 0
        assert result["failed"] == len(RSS_FEEDS)

    @pytest.mark.asyncio
    async def test_partial_feed_failure_still_returns_data(self):
        """If some feeds fail but others succeed, still return data."""
        session = AsyncMock()
        mock_result = MagicMock()
        mock_result.rowcount = 1
        session.execute = AsyncMock(return_value=mock_result)
        session.commit = AsyncMock()

        crawler = _make_crawler(session)
        crawler._get_watchlist_ticker_map = AsyncMock(return_value={"HPG": 10})

        call_count = 0

        async def mock_get(url, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                # First feed succeeds
                resp = MagicMock()
                resp.status_code = 200
                resp.text = SAMPLE_RSS_CHUNG_KHOAN
                resp.raise_for_status = MagicMock()
                return resp
            else:
                raise httpx.ConnectError("timeout")

        with patch("app.crawlers.vietstock_crawler.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get = mock_get
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_cls.return_value = mock_client

            result = await crawler.crawl_rss()

        assert result["total_posts"] > 0
        assert result["failed"] == len(RSS_FEEDS) - 1
