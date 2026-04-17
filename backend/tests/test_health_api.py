"""Tests for health monitoring API endpoints."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


def mock_async_session():
    """Create mock async session context manager."""
    mock_session = AsyncMock()
    mock_cm = AsyncMock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_session)
    mock_cm.__aexit__ = AsyncMock(return_value=False)
    mock_factory = MagicMock(return_value=mock_cm)
    return mock_factory, mock_session


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
                from fastapi.testclient import TestClient
                yield TestClient(app)


SAMPLE_JOBS = [
    {
        "job_id": "daily_price_crawl",
        "job_name": "Daily Price Crawl",
        "status": "success",
        "color": "green",
        "started_at": "2025-07-01T09:00:00+07:00",
        "completed_at": "2025-07-01T09:05:00+07:00",
        "duration_seconds": 300.0,
        "result_summary": {"tickers_updated": 400},
        "error_message": None,
    },
    {
        "job_id": "daily_indicator_compute_triggered",
        "job_name": "Daily Indicator Compute",
        "status": "partial",
        "color": "yellow",
        "started_at": "2025-07-01T09:10:00+07:00",
        "completed_at": "2025-07-01T09:12:00+07:00",
        "duration_seconds": 120.0,
        "result_summary": {"computed": 380},
        "error_message": None,
    },
    {
        "job_id": "daily_ai_analysis_triggered",
        "job_name": "Daily AI Analysis",
        "status": "failed",
        "color": "red",
        "started_at": "2025-07-01T09:15:00+07:00",
        "completed_at": None,
        "duration_seconds": None,
        "result_summary": None,
        "error_message": "API rate limit exceeded",
    },
]

SAMPLE_FRESHNESS = [
    {"data_type": "Giá cổ phiếu", "table_name": "daily_prices", "latest": "2025-07-01", "is_stale": False, "threshold_hours": 48},
    {"data_type": "Chỉ báo kỹ thuật", "table_name": "technical_indicators", "latest": "2025-07-01", "is_stale": False, "threshold_hours": 48},
    {"data_type": "Phân tích AI", "table_name": "ai_analyses", "latest": "2025-06-28", "is_stale": True, "threshold_hours": 48},
    {"data_type": "Tin tức", "table_name": "news_articles", "latest": "2025-07-01T08:00:00+07:00", "is_stale": False, "threshold_hours": 48},
    {"data_type": "Báo cáo tài chính", "table_name": "financials", "latest": "2025-06-25T10:00:00+07:00", "is_stale": False, "threshold_hours": 168},
]


class TestHealthJobs:
    """Tests for GET /api/health/jobs."""

    def test_jobs_returns_200_with_status(self, client):
        """Jobs endpoint returns 200 with correct structure."""
        factory, _ = mock_async_session()
        with patch("app.api.health.async_session", factory), \
             patch("app.services.health_service.HealthService.get_job_statuses", new_callable=AsyncMock, return_value=SAMPLE_JOBS):
            resp = client.get("/api/health/jobs")
        assert resp.status_code == 200
        data = resp.json()
        assert "jobs" in data
        assert len(data["jobs"]) == 3
        assert data["jobs"][0]["job_id"] == "daily_price_crawl"

    def test_jobs_color_mapping(self, client):
        """Color maps correctly: success→green, partial→yellow, failed→red."""
        factory, _ = mock_async_session()
        with patch("app.api.health.async_session", factory), \
             patch("app.services.health_service.HealthService.get_job_statuses", new_callable=AsyncMock, return_value=SAMPLE_JOBS):
            resp = client.get("/api/health/jobs")
        data = resp.json()
        colors = {j["status"]: j["color"] for j in data["jobs"]}
        assert colors["success"] == "green"
        assert colors["partial"] == "yellow"
        assert colors["failed"] == "red"


class TestDataFreshness:
    """Tests for GET /api/health/data-freshness."""

    def test_freshness_returns_200(self, client):
        """Freshness endpoint returns 5 items with correct fields."""
        factory, _ = mock_async_session()
        with patch("app.api.health.async_session", factory), \
             patch("app.services.health_service.HealthService.get_data_freshness", new_callable=AsyncMock, return_value=SAMPLE_FRESHNESS):
            resp = client.get("/api/health/data-freshness")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["items"]) == 5
        for item in data["items"]:
            assert "data_type" in item
            assert "is_stale" in item
            assert "threshold_hours" in item

    def test_freshness_stale_flag(self, client):
        """Stale items are correctly flagged."""
        factory, _ = mock_async_session()
        with patch("app.api.health.async_session", factory), \
             patch("app.services.health_service.HealthService.get_data_freshness", new_callable=AsyncMock, return_value=SAMPLE_FRESHNESS):
            resp = client.get("/api/health/data-freshness")
        stale = [i for i in resp.json()["items"] if i["is_stale"]]
        assert len(stale) == 1
        assert stale[0]["table_name"] == "ai_analyses"


class TestErrorRates:
    """Tests for GET /api/health/errors."""

    SAMPLE_ERRORS = [
        {
            "job_id": "daily_price_crawl",
            "job_name": "Daily Price Crawl",
            "days": [
                {"day": "2025-06-30", "total": 2, "failed": 0},
                {"day": "2025-07-01", "total": 1, "failed": 1},
            ],
            "total_runs": 3,
            "total_failures": 1,
        },
    ]

    def test_errors_returns_200(self, client):
        """Error rates endpoint returns 200 with jobs list."""
        factory, _ = mock_async_session()
        with patch("app.api.health.async_session", factory), \
             patch("app.services.health_service.HealthService.get_error_rates", new_callable=AsyncMock, return_value=self.SAMPLE_ERRORS):
            resp = client.get("/api/health/errors")
        assert resp.status_code == 200
        assert "jobs" in resp.json()

    def test_errors_totals(self, client):
        """Total runs and failures match sum of day data."""
        factory, _ = mock_async_session()
        with patch("app.api.health.async_session", factory), \
             patch("app.services.health_service.HealthService.get_error_rates", new_callable=AsyncMock, return_value=self.SAMPLE_ERRORS):
            resp = client.get("/api/health/errors")
        job = resp.json()["jobs"][0]
        assert job["total_runs"] == sum(d["total"] for d in job["days"])
        assert job["total_failures"] == sum(d["failed"] for d in job["days"])


class TestDbPool:
    """Tests for GET /api/health/db-pool."""

    def test_pool_returns_200(self, client):
        """DB pool endpoint returns all stat fields."""
        mock_pool = MagicMock()
        mock_pool.size.return_value = 5
        mock_pool.checkedin.return_value = 3
        mock_pool.checkedout.return_value = 2
        mock_pool.overflow.return_value = 0
        with patch("app.api.health.engine") as mock_engine:
            mock_engine.pool = mock_pool
            resp = client.get("/api/health/db-pool")
        assert resp.status_code == 200
        data = resp.json()
        assert data["pool_size"] == 5
        assert data["checked_in"] == 3
        assert data["checked_out"] == 2
        assert data["overflow"] == 0
        assert data["max_overflow"] == 3


class TestJobTrigger:
    """Tests for POST /api/health/trigger/{job_name}."""

    def test_trigger_known_job(self, client):
        """POST trigger/crawl returns 200 and calls scheduler.add_job."""
        mock_jobs = MagicMock()
        mock_jobs.daily_price_crawl = MagicMock()
        with patch("app.api.health.scheduler") as mock_sched, \
             patch.dict("sys.modules", {"app.scheduler.jobs": mock_jobs}):
            resp = client.post("/api/health/trigger/crawl")
        assert resp.status_code == 200
        data = resp.json()
        assert data["triggered"] is True
        mock_sched.add_job.assert_called_once()
        call_kwargs = mock_sched.add_job.call_args
        assert call_kwargs.kwargs.get("id") == "daily_price_crawl_manual"
        assert call_kwargs.kwargs.get("replace_existing") is True

    def test_trigger_unknown_job(self, client):
        """POST trigger/invalid returns 404."""
        resp = client.post("/api/health/trigger/invalid_xyz")
        assert resp.status_code == 404
        assert "Unknown job" in resp.json()["detail"]

    def test_trigger_all_valid_names(self, client):
        """All 6 valid job names return 200."""
        mock_jobs = MagicMock()
        for name in ["crawl", "indicators", "ai", "news", "sentiment", "combined"]:
            with patch("app.api.health.scheduler") as mock_sched, \
                 patch.dict("sys.modules", {"app.scheduler.jobs": mock_jobs}):
                resp = client.post(f"/api/health/trigger/{name}")
            assert resp.status_code == 200, f"Job '{name}' failed: {resp.text}"


class TestHealthSummary:
    """Tests for GET /api/health/summary."""

    def test_summary_healthy(self, client):
        """All green + no stale → status='healthy'."""
        healthy_jobs = [{"job_id": "x", "job_name": "X", "status": "success", "color": "green",
                        "started_at": None, "completed_at": None, "duration_seconds": None,
                        "result_summary": None, "error_message": None}]
        fresh_items = [{"data_type": "t", "table_name": "t", "latest": "2025-07-01", "is_stale": False, "threshold_hours": 48}]
        factory, _ = mock_async_session()
        mock_pool = MagicMock()
        mock_pool.size.return_value = 5
        mock_pool.checkedin.return_value = 5
        mock_pool.checkedout.return_value = 0
        mock_pool.overflow.return_value = 0
        with patch("app.api.health.async_session", factory), \
             patch("app.services.health_service.HealthService.get_job_statuses", new_callable=AsyncMock, return_value=healthy_jobs), \
             patch("app.services.health_service.HealthService.get_data_freshness", new_callable=AsyncMock, return_value=fresh_items), \
             patch("app.api.health.engine") as mock_engine:
            mock_engine.pool = mock_pool
            resp = client.get("/api/health/summary")
        assert resp.status_code == 200
        assert resp.json()["status"] == "healthy"

    def test_summary_degraded(self, client):
        """One red job → status='degraded'."""
        red_jobs = [{"job_id": "x", "job_name": "X", "status": "failed", "color": "red",
                    "started_at": None, "completed_at": None, "duration_seconds": None,
                    "result_summary": None, "error_message": "err"}]
        fresh_items = [{"data_type": "t", "table_name": "t", "latest": "2025-07-01", "is_stale": False, "threshold_hours": 48}]
        factory, _ = mock_async_session()
        mock_pool = MagicMock()
        mock_pool.size.return_value = 5
        mock_pool.checkedin.return_value = 5
        mock_pool.checkedout.return_value = 0
        mock_pool.overflow.return_value = 0
        with patch("app.api.health.async_session", factory), \
             patch("app.services.health_service.HealthService.get_job_statuses", new_callable=AsyncMock, return_value=red_jobs), \
             patch("app.services.health_service.HealthService.get_data_freshness", new_callable=AsyncMock, return_value=fresh_items), \
             patch("app.api.health.engine") as mock_engine:
            mock_engine.pool = mock_pool
            resp = client.get("/api/health/summary")
        assert resp.status_code == 200
        assert resp.json()["status"] == "degraded"
