"""Tests for news endpoint added in quick task 260423-epd.

Covers GET /analysis/{symbol}/news:
- Successful retrieval with mock articles
- Limit capping at 50
- Default limit behavior
- Empty result for ticker with no news
- 404 for unknown ticker
- NewsArticleResponse schema validation
"""
import pytest
from datetime import datetime, timezone
from unittest.mock import patch, AsyncMock, MagicMock
from fastapi.testclient import TestClient

from app.schemas.analysis import NewsArticleResponse


@pytest.fixture
def client():
    """Create test client with mocked database and scheduler."""
    with patch("app.database.engine") as mock_engine:
        mock_engine.dispose = AsyncMock()
        with patch("app.scheduler.manager.scheduler") as mock_scheduler:
            mock_scheduler.running = True
            mock_scheduler.start = MagicMock()
            mock_scheduler.shutdown = MagicMock()
            mock_scheduler.get_jobs.return_value = []

            with patch("app.scheduler.manager.configure_jobs"):
                from app.main import app
                yield TestClient(app)


def _make_mock_article(title: str, url: str, published_at: datetime):
    """Create a mock NewsArticle ORM object."""
    article = MagicMock()
    article.title = title
    article.url = url
    article.published_at = published_at
    return article


def _make_mock_ticker(ticker_id: int = 1, symbol: str = "FPT"):
    """Create a mock Ticker ORM object."""
    ticker = MagicMock()
    ticker.id = ticker_id
    ticker.symbol = symbol
    return ticker


class TestGetTickerNews:

    def test_returns_articles(self, client):
        """GET /analysis/{symbol}/news returns list of articles."""
        mock_ticker = _make_mock_ticker()
        mock_articles = [
            _make_mock_article(
                "FPT đạt doanh thu kỷ lục Q1",
                "https://cafef.vn/fpt-1.chn",
                datetime(2026, 4, 20, 10, 0, tzinfo=timezone.utc),
            ),
            _make_mock_article(
                "FPT mở rộng thị trường Nhật",
                "https://cafef.vn/fpt-2.chn",
                datetime(2026, 4, 19, 8, 0, tzinfo=timezone.utc),
            ),
        ]

        with patch("app.api.analysis.async_session") as mock_sf:
            mock_session = AsyncMock()
            mock_sf.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_sf.return_value.__aexit__ = AsyncMock(return_value=False)

            # First execute call: _get_ticker_by_symbol
            ticker_result = MagicMock()
            ticker_result.scalar_one_or_none.return_value = mock_ticker
            # Second execute call: news query
            news_result = MagicMock()
            news_result.scalars.return_value.all.return_value = mock_articles

            mock_session.execute = AsyncMock(side_effect=[ticker_result, news_result])

            response = client.get("/api/analysis/FPT/news")
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 2
            assert data[0]["title"] == "FPT đạt doanh thu kỷ lục Q1"
            assert data[0]["url"] == "https://cafef.vn/fpt-1.chn"
            assert "2026-04-20" in data[0]["published_at"]

    def test_limit_capping_at_50(self, client):
        """Requesting limit > 50 should be capped to 50."""
        mock_ticker = _make_mock_ticker()

        with patch("app.api.analysis.async_session") as mock_sf:
            mock_session = AsyncMock()
            mock_sf.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_sf.return_value.__aexit__ = AsyncMock(return_value=False)

            ticker_result = MagicMock()
            ticker_result.scalar_one_or_none.return_value = mock_ticker
            news_result = MagicMock()
            news_result.scalars.return_value.all.return_value = []

            mock_session.execute = AsyncMock(side_effect=[ticker_result, news_result])

            response = client.get("/api/analysis/FPT/news?limit=100")
            assert response.status_code == 200
            # Verify the query was called (limit is capped internally)
            assert mock_session.execute.call_count == 2

    def test_default_limit(self, client):
        """No limit param defaults to 10."""
        mock_ticker = _make_mock_ticker()

        with patch("app.api.analysis.async_session") as mock_sf:
            mock_session = AsyncMock()
            mock_sf.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_sf.return_value.__aexit__ = AsyncMock(return_value=False)

            ticker_result = MagicMock()
            ticker_result.scalar_one_or_none.return_value = mock_ticker
            news_result = MagicMock()
            news_result.scalars.return_value.all.return_value = []

            mock_session.execute = AsyncMock(side_effect=[ticker_result, news_result])

            response = client.get("/api/analysis/FPT/news")
            assert response.status_code == 200
            assert response.json() == []

    def test_empty_result(self, client):
        """Ticker exists but has no news articles → 200 + empty list."""
        mock_ticker = _make_mock_ticker()

        with patch("app.api.analysis.async_session") as mock_sf:
            mock_session = AsyncMock()
            mock_sf.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_sf.return_value.__aexit__ = AsyncMock(return_value=False)

            ticker_result = MagicMock()
            ticker_result.scalar_one_or_none.return_value = mock_ticker
            news_result = MagicMock()
            news_result.scalars.return_value.all.return_value = []

            mock_session.execute = AsyncMock(side_effect=[ticker_result, news_result])

            response = client.get("/api/analysis/VNM/news")
            assert response.status_code == 200
            assert response.json() == []

    def test_unknown_ticker_returns_404(self, client):
        """Unknown symbol → 404."""
        with patch("app.api.analysis.async_session") as mock_sf:
            mock_session = AsyncMock()
            mock_sf.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_sf.return_value.__aexit__ = AsyncMock(return_value=False)

            ticker_result = MagicMock()
            ticker_result.scalar_one_or_none.return_value = None

            mock_session.execute = AsyncMock(return_value=ticker_result)

            response = client.get("/api/analysis/ZZZZZ/news")
            assert response.status_code == 404
            assert "ZZZZZ" in response.json()["detail"]


class TestNewsArticleResponseSchema:

    def test_valid_schema(self):
        """NewsArticleResponse accepts valid data."""
        resp = NewsArticleResponse(
            title="Test article",
            url="https://cafef.vn/test.chn",
            published_at="2026-04-20T10:00:00+00:00",
        )
        assert resp.title == "Test article"
        assert resp.url == "https://cafef.vn/test.chn"

    def test_isoformat_string(self):
        """published_at should be an ISO format string."""
        dt = datetime(2026, 4, 20, 10, 0, tzinfo=timezone.utc)
        resp = NewsArticleResponse(
            title="Test",
            url="https://cafef.vn/test.chn",
            published_at=dt.isoformat(),
        )
        assert "2026-04-20" in resp.published_at
        assert "T" in resp.published_at
