"""Tests for API endpoints."""
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """Create test client with mocked database and scheduler."""
    # Must patch before importing app to avoid real DB connection
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


class TestHealthEndpoint:

    def test_health_returns_200(self, client):
        """Health endpoint must return 200 with status fields."""
        with patch("app.api.system.engine") as mock_engine:
            mock_conn = AsyncMock()
            mock_conn.execute = AsyncMock()
            mock_engine.connect = MagicMock()
            mock_engine.connect.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
            mock_engine.connect.return_value.__aexit__ = AsyncMock(return_value=False)

            response = client.get("/api/health")
            assert response.status_code == 200
            data = response.json()
            assert "status" in data
            assert "database" in data
            assert "scheduler" in data
            assert "timestamp" in data

    def test_root_returns_ok(self, client):
        """Root endpoint must return status ok."""
        response = client.get("/")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"


class TestSchedulerEndpoint:

    def test_scheduler_status_returns_200(self, client):
        """Scheduler status endpoint must return running state and jobs list."""
        with patch("app.api.system.scheduler") as mock_sched:
            mock_sched.running = True
            mock_sched.get_jobs.return_value = []

            response = client.get("/api/scheduler/status")
            assert response.status_code == 200
            data = response.json()
            assert "running" in data
            assert "jobs" in data
            assert isinstance(data["jobs"], list)


class TestCrawlTriggerEndpoints:
    """Tests for manual crawl trigger endpoints.

    Background tasks run synchronously in TestClient, so we must mock
    async_session and service classes to prevent real DB connections.
    """

    def test_trigger_daily_crawl_returns_200(self, client):
        """POST /api/crawl/daily must return triggered=true."""
        with patch("app.api.system.async_session") as mock_sf:
            mock_session = AsyncMock()
            mock_sf.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_sf.return_value.__aexit__ = AsyncMock(return_value=False)
            with patch("app.api.system.PriceService") as MockPS:
                MockPS.return_value = AsyncMock()
                response = client.post("/api/crawl/daily")
                assert response.status_code == 200
                assert response.json()["triggered"] is True

    def test_trigger_ticker_sync_returns_200(self, client):
        """POST /api/crawl/tickers must return triggered=true."""
        with patch("app.api.system.async_session") as mock_sf:
            mock_session = AsyncMock()
            mock_sf.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_sf.return_value.__aexit__ = AsyncMock(return_value=False)
            with patch("app.api.system.TickerService") as MockTS:
                MockTS.return_value = AsyncMock()
                response = client.post("/api/crawl/tickers")
                assert response.status_code == 200
                assert response.json()["triggered"] is True

    def test_trigger_financial_crawl_returns_200(self, client):
        """POST /api/crawl/financials must return triggered=true."""
        with patch("app.api.system.async_session") as mock_sf:
            mock_session = AsyncMock()
            mock_sf.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_sf.return_value.__aexit__ = AsyncMock(return_value=False)
            with patch("app.api.system.FinancialService") as MockFS:
                MockFS.return_value = AsyncMock()
                response = client.post("/api/crawl/financials")
                assert response.status_code == 200
                assert response.json()["triggered"] is True

    def test_trigger_backfill_returns_200(self, client):
        """POST /api/backfill must return triggered=true."""
        with patch("app.api.system.async_session") as mock_sf:
            mock_session = AsyncMock()
            mock_sf.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_sf.return_value.__aexit__ = AsyncMock(return_value=False)
            with patch("app.api.system.TickerService") as MockTS, \
                 patch("app.api.system.PriceService") as MockPS, \
                 patch("app.api.system.FinancialService") as MockFS:
                MockTS.return_value = AsyncMock()
                MockPS.return_value = AsyncMock()
                MockFS.return_value = AsyncMock()
                response = client.post("/api/backfill")
                assert response.status_code == 200
                assert response.json()["triggered"] is True
