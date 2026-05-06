"""Tests for VnExpress RSS crawler — parsing, ticker matching, dedup."""
import pytest
import httpx
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from app.crawlers.vnexpress_crawler import (
    VnExpressCrawler,
    _guid_to_post_id,
    _strip_html,
    FALSE_POSITIVES,
)


# --- Sample VnExpress RSS XML ---

SAMPLE_RSS = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
<channel>
    <title>Kinh doanh - VnExpress RSS</title>
    <item>
        <title>HPG báo lãi kỷ lục quý 2, cổ phiếu tăng mạnh</title>
        <description><![CDATA[<a href="..."><img src="https://img.vne.vn/test.jpg"/></a><br/>Hòa Phát (HPG) công bố kết quả kinh doanh Q2 với lợi nhuận tăng 45% so với cùng kỳ.]]></description>
        <pubDate>Wed, 06 May 2026 08:24:07 +0700</pubDate>
        <link>https://vnexpress.net/hpg-bao-lai-ky-luc-1234567.html</link>
        <guid>https://vnexpress.net/hpg-bao-lai-ky-luc-1234567.html</guid>
    </item>
    <item>
        <title>GDP Việt Nam tăng 6.5% trong nửa đầu năm</title>
        <description>Tổng sản phẩm quốc nội tăng mạnh nhờ FDI và xuất khẩu.</description>
        <pubDate>Wed, 06 May 2026 07:00:00 +0700</pubDate>
        <link>https://vnexpress.net/gdp-viet-nam-tang-9876543.html</link>
        <guid>https://vnexpress.net/gdp-viet-nam-tang-9876543.html</guid>
    </item>
    <item>
        <title>VNM và MWG dẫn đầu nhóm tiêu dùng</title>
        <description>Vinamilk (VNM) và Thế Giới Di Động (MWG) ghi nhận doanh thu tăng trưởng hai chữ số.</description>
        <pubDate>Wed, 06 May 2026 06:30:00 +0700</pubDate>
        <link>https://vnexpress.net/vnm-mwg-dan-dau-5555555.html</link>
        <guid>https://vnexpress.net/vnm-mwg-dan-dau-5555555.html</guid>
    </item>
    <item>
        <title>Short post</title>
        <description>Too short</description>
        <pubDate>Wed, 06 May 2026 05:00:00 +0700</pubDate>
        <link>https://vnexpress.net/short-1111.html</link>
        <guid>https://vnexpress.net/short-1111.html</guid>
    </item>
</channel>
</rss>"""


def _make_crawler(session=None):
    """Create VnExpressCrawler without real DB."""
    crawler = VnExpressCrawler.__new__(VnExpressCrawler)
    crawler.session = session or AsyncMock()
    crawler.headers = {"User-Agent": "test"}
    return crawler


class TestRSSParsing:
    """Test _parse_rss extracts articles correctly."""

    def test_parse_all_items(self):
        crawler = _make_crawler()
        items = crawler._parse_rss(SAMPLE_RSS)
        assert len(items) == 4

    def test_parse_title_in_content(self):
        crawler = _make_crawler()
        items = crawler._parse_rss(SAMPLE_RSS)
        # Content should include title prefix
        assert items[0]["content"].startswith("HPG báo lãi kỷ lục")

    def test_parse_strips_html(self):
        crawler = _make_crawler()
        items = crawler._parse_rss(SAMPLE_RSS)
        # HTML tags should be stripped from description
        assert "<img" not in items[0]["content"]
        assert "<a " not in items[0]["content"]

    def test_parse_pubdate(self):
        crawler = _make_crawler()
        items = crawler._parse_rss(SAMPLE_RSS)
        assert items[0]["pub_date"].year == 2026
        assert items[0]["pub_date"].tzinfo is not None

    def test_parse_guid(self):
        crawler = _make_crawler()
        items = crawler._parse_rss(SAMPLE_RSS)
        assert "1234567" in items[0]["guid"]


class TestHelpers:
    """Test helper functions."""

    def test_guid_to_post_id_deterministic(self):
        id1 = _guid_to_post_id("vnexpress:https://vnexpress.net/test-123.html:HPG")
        id2 = _guid_to_post_id("vnexpress:https://vnexpress.net/test-123.html:HPG")
        assert id1 == id2

    def test_guid_to_post_id_different_for_different_tickers(self):
        id1 = _guid_to_post_id("vnexpress:https://vnexpress.net/test.html:HPG")
        id2 = _guid_to_post_id("vnexpress:https://vnexpress.net/test.html:VNM")
        assert id1 != id2

    def test_strip_html_removes_tags(self):
        assert _strip_html("<b>Hello</b> <i>world</i>") == "Hello world"

    def test_strip_html_decodes_entities(self):
        assert "ứ" in _strip_html("tin t&#7913;c")

    def test_false_positives_excludes_common_words(self):
        assert "CEO" in FALSE_POSITIVES
        assert "GDP" in FALSE_POSITIVES
        assert "IPO" in FALSE_POSITIVES
        assert "HPG" not in FALSE_POSITIVES


class TestTickerMatching:
    """Test ticker extraction and matching logic."""

    @pytest.mark.asyncio
    async def test_crawl_matches_watchlist_tickers(self):
        """Only watchlist tickers should be stored."""
        session = AsyncMock()
        # Mock execute to return rowcount=1 (inserted)
        mock_result = MagicMock()
        mock_result.rowcount = 1
        session.execute = AsyncMock(return_value=mock_result)
        session.commit = AsyncMock()

        crawler = _make_crawler(session)

        # Mock watchlist with HPG and VNM
        ticker_map = {"HPG": 10, "VNM": 20, "MWG": 30}
        crawler._get_watchlist_ticker_map = AsyncMock(return_value=ticker_map)

        # Mock HTTP response
        with patch("app.crawlers.vnexpress_crawler.httpx.AsyncClient") as mock_client_cls:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.text = SAMPLE_RSS
            mock_response.raise_for_status = MagicMock()

            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_cls.return_value = mock_client

            result = await crawler.crawl_rss()

        # HPG article + VNM/MWG article should match
        assert result["total_posts"] > 0
        assert result["success"] > 0

    @pytest.mark.asyncio
    async def test_crawl_empty_watchlist_skips(self):
        """Empty watchlist should return zero results."""
        crawler = _make_crawler()
        crawler._get_watchlist_ticker_map = AsyncMock(return_value={})

        result = await crawler.crawl_rss()

        assert result["total_posts"] == 0
        assert result["success"] == 0

    @pytest.mark.asyncio
    async def test_crawl_http_error_returns_failure(self):
        """HTTP error should return failed result, not crash."""
        session = AsyncMock()
        crawler = _make_crawler(session)
        crawler._get_watchlist_ticker_map = AsyncMock(return_value={"HPG": 10})

        with patch("app.crawlers.vnexpress_crawler.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(side_effect=httpx.ConnectError("timeout"))
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_cls.return_value = mock_client

            result = await crawler.crawl_rss()

        assert result["failed"] == 1
        assert "RSS" in result["failed_symbols"]


class TestFalsePositiveFiltering:
    """Test that common 3-letter words are not matched as tickers."""

    def test_gdp_not_matched(self):
        """GDP in article title should not be treated as a ticker."""
        crawler = _make_crawler()
        items = crawler._parse_rss(SAMPLE_RSS)
        # The GDP article mentions GDP, FDI — these are in FALSE_POSITIVES
        gdp_article = items[1]
        import re
        from app.crawlers.vnexpress_crawler import TICKER_PATTERN
        mentioned = TICKER_PATTERN.findall(f"{gdp_article['title']} {gdp_article['content']}")
        matched = {t for t in mentioned if t not in FALSE_POSITIVES}
        # GDP and FDI should be filtered out
        assert "GDP" not in matched
        assert "FDI" not in matched
