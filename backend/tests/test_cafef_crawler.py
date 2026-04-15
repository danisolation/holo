"""Tests for CafeF news crawler — HTML parsing and article extraction."""
import pytest
from datetime import datetime, timedelta


class TestCafeFCrawlerParsing:
    """Test HTML parsing without network calls."""

    def _make_crawler(self):
        """Create a CafeFCrawler instance without DB session (for parsing tests only)."""
        from app.crawlers.cafef_crawler import CafeFCrawler
        crawler = CafeFCrawler.__new__(CafeFCrawler)
        crawler.news_days = 7
        crawler.delay = 0
        crawler.headers = {}
        return crawler

    def test_parse_articles_extracts_title_and_url(self):
        """Parser must extract title text and href from docnhanhTitle link."""
        crawler = self._make_crawler()
        now = datetime.now()
        date_str = now.strftime("%d/%m/%Y %H:%M")
        html = f'<ul><li><span class="timeTitle">{date_str}</span><a class="docnhanhTitle" href="/test-article.chn" title="Full Title">Short Title</a></li></ul>'

        articles = crawler._parse_articles(html)
        assert len(articles) == 1
        assert articles[0]["title"] == "Short Title"
        assert articles[0]["url"] == "https://cafef.vn/test-article.chn"
        assert articles[0]["source"] == "cafef"

    def test_parse_articles_filters_old_articles(self):
        """Parser must exclude articles older than news_days window."""
        crawler = self._make_crawler()
        old_date = (datetime.now() - timedelta(days=10)).strftime("%d/%m/%Y %H:%M")
        html = f'<ul><li><span class="timeTitle">{old_date}</span><a class="docnhanhTitle" href="/old.chn">Old Article</a></li></ul>'

        articles = crawler._parse_articles(html)
        assert len(articles) == 0

    def test_parse_articles_handles_empty_html(self):
        """Parser must return empty list for empty or no-article HTML."""
        crawler = self._make_crawler()
        assert crawler._parse_articles("") == []
        assert crawler._parse_articles("<html></html>") == []
        assert crawler._parse_articles("<ul></ul>") == []

    def test_parse_articles_normalizes_relative_urls(self):
        """Parser must prepend base URL to relative URLs."""
        crawler = self._make_crawler()
        now = datetime.now().strftime("%d/%m/%Y %H:%M")
        html = f'<ul><li><span class="timeTitle">{now}</span><a class="docnhanhTitle" href="/du-lieu/VNM-123/article.chn">Title</a></li></ul>'

        articles = crawler._parse_articles(html)
        assert articles[0]["url"].startswith("https://cafef.vn/")

    def test_parse_articles_keeps_absolute_urls(self):
        """Parser must not double-prefix already absolute URLs."""
        crawler = self._make_crawler()
        now = datetime.now().strftime("%d/%m/%Y %H:%M")
        html = f'<ul><li><span class="timeTitle">{now}</span><a class="docnhanhTitle" href="https://cafef.vn/article.chn">Title</a></li></ul>'

        articles = crawler._parse_articles(html)
        assert articles[0]["url"] == "https://cafef.vn/article.chn"

    def test_parse_articles_skips_malformed_date(self):
        """Parser must skip articles with unparseable dates."""
        crawler = self._make_crawler()
        html = '<ul><li><span class="timeTitle">not-a-date</span><a class="docnhanhTitle" href="/a.chn">Title</a></li></ul>'

        articles = crawler._parse_articles(html)
        assert len(articles) == 0

    def test_parse_articles_skips_missing_link(self):
        """Parser must skip <li> elements without docnhanhTitle link."""
        crawler = self._make_crawler()
        now = datetime.now().strftime("%d/%m/%Y %H:%M")
        html = f'<ul><li><span class="timeTitle">{now}</span><span>No link here</span></li></ul>'

        articles = crawler._parse_articles(html)
        assert len(articles) == 0

    def test_parse_articles_multiple(self):
        """Parser must extract multiple articles from a list."""
        crawler = self._make_crawler()
        now = datetime.now().strftime("%d/%m/%Y %H:%M")
        html = f"""<ul>
            <li><span class="timeTitle">{now}</span><a class="docnhanhTitle" href="/a1.chn">Article 1</a></li>
            <li><span class="timeTitle">{now}</span><a class="docnhanhTitle" href="/a2.chn">Article 2</a></li>
            <li><span class="timeTitle">{now}</span><a class="docnhanhTitle" href="/a3.chn">Article 3</a></li>
        </ul>"""

        articles = crawler._parse_articles(html)
        assert len(articles) == 3
        assert articles[0]["title"] == "Article 1"
        assert articles[2]["title"] == "Article 3"
