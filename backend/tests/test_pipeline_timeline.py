"""Tests for pipeline timeline API endpoint (Phase 15-02, T-15-04).

Tests cover:
- PipelineTimelineResponse schema structure
- Grouping by date
- Duration computation from completed_at - started_at
- Days parameter default and max cap
- Empty result handling
- Vietnamese job name mapping
"""
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch


# ---- Service Tests ----

class TestPipelineTimelineService:
    """Tests for HealthService.get_pipeline_timeline."""

    @pytest.fixture
    def mock_session(self):
        session = AsyncMock()
        session.execute = AsyncMock()
        return session

    def _make_row(self, job_id, started_at, completed_at, status):
        """Helper to create a mock row."""
        row = MagicMock()
        row.job_id = job_id
        row.started_at = started_at
        row.completed_at = completed_at
        row.status = status
        return row

    @pytest.mark.asyncio
    async def test_returns_correct_structure(self, mock_session):
        """get_pipeline_timeline returns runs grouped by date with steps."""
        from app.services.health_service import HealthService

        dt1 = datetime(2026, 4, 17, 8, 0, 0, tzinfo=timezone.utc)
        dt1_end = datetime(2026, 4, 17, 8, 5, 0, tzinfo=timezone.utc)

        mock_result = MagicMock()
        mock_result.fetchall.return_value = [
            self._make_row("daily_price_crawl_hose", dt1, dt1_end, "success"),
        ]
        mock_session.execute = AsyncMock(return_value=mock_result)

        svc = HealthService(mock_session)
        result = await svc.get_pipeline_timeline(days=7)

        assert isinstance(result, list)
        assert len(result) == 1
        run = result[0]
        assert "date" in run
        assert "total_seconds" in run
        assert "steps" in run
        assert len(run["steps"]) == 1
        step = run["steps"][0]
        assert "job_id" in step
        assert "job_name" in step
        assert "started_at" in step
        assert "duration_seconds" in step
        assert "status" in step

    @pytest.mark.asyncio
    async def test_grouping_by_date(self, mock_session):
        """Jobs on same date are grouped into a single run."""
        from app.services.health_service import HealthService

        day1_dt1 = datetime(2026, 4, 17, 8, 0, 0, tzinfo=timezone.utc)
        day1_dt1_end = datetime(2026, 4, 17, 8, 5, 0, tzinfo=timezone.utc)
        day1_dt2 = datetime(2026, 4, 17, 8, 10, 0, tzinfo=timezone.utc)
        day1_dt2_end = datetime(2026, 4, 17, 8, 12, 0, tzinfo=timezone.utc)
        day2_dt1 = datetime(2026, 4, 16, 9, 0, 0, tzinfo=timezone.utc)
        day2_dt1_end = datetime(2026, 4, 16, 9, 3, 0, tzinfo=timezone.utc)

        mock_result = MagicMock()
        mock_result.fetchall.return_value = [
            self._make_row("daily_price_crawl_hose", day1_dt1, day1_dt1_end, "success"),
            self._make_row("daily_indicator_compute_triggered", day1_dt2, day1_dt2_end, "success"),
            self._make_row("daily_price_crawl_hose", day2_dt1, day2_dt1_end, "success"),
        ]
        mock_session.execute = AsyncMock(return_value=mock_result)

        svc = HealthService(mock_session)
        result = await svc.get_pipeline_timeline(days=7)

        assert len(result) == 2
        # First run (most recent date) has 2 steps
        dates = [r["date"] for r in result]
        assert "2026-04-17" in dates
        assert "2026-04-16" in dates
        run_17 = next(r for r in result if r["date"] == "2026-04-17")
        assert len(run_17["steps"]) == 2

    @pytest.mark.asyncio
    async def test_duration_computation(self, mock_session):
        """Duration is computed as (completed_at - started_at).total_seconds()."""
        from app.services.health_service import HealthService

        dt_start = datetime(2026, 4, 17, 8, 0, 0, tzinfo=timezone.utc)
        dt_end = datetime(2026, 4, 17, 8, 5, 30, tzinfo=timezone.utc)

        mock_result = MagicMock()
        mock_result.fetchall.return_value = [
            self._make_row("daily_price_crawl_hose", dt_start, dt_end, "success"),
        ]
        mock_session.execute = AsyncMock(return_value=mock_result)

        svc = HealthService(mock_session)
        result = await svc.get_pipeline_timeline(days=7)

        step = result[0]["steps"][0]
        assert step["duration_seconds"] == 330.0  # 5min 30sec

    @pytest.mark.asyncio
    async def test_duration_none_when_not_completed(self, mock_session):
        """Duration is None when completed_at is None (running/failed)."""
        from app.services.health_service import HealthService

        dt_start = datetime(2026, 4, 17, 8, 0, 0, tzinfo=timezone.utc)

        mock_result = MagicMock()
        mock_result.fetchall.return_value = [
            self._make_row("daily_price_crawl_hose", dt_start, None, "failed"),
        ]
        mock_session.execute = AsyncMock(return_value=mock_result)

        svc = HealthService(mock_session)
        result = await svc.get_pipeline_timeline(days=7)

        step = result[0]["steps"][0]
        assert step["duration_seconds"] is None

    @pytest.mark.asyncio
    async def test_total_seconds_sums_durations(self, mock_session):
        """total_seconds for a run sums all step durations (skipping None)."""
        from app.services.health_service import HealthService

        dt1 = datetime(2026, 4, 17, 8, 0, 0, tzinfo=timezone.utc)
        dt1_end = datetime(2026, 4, 17, 8, 5, 0, tzinfo=timezone.utc)  # 300s
        dt2 = datetime(2026, 4, 17, 8, 10, 0, tzinfo=timezone.utc)
        dt2_end = datetime(2026, 4, 17, 8, 12, 0, tzinfo=timezone.utc)  # 120s

        mock_result = MagicMock()
        mock_result.fetchall.return_value = [
            self._make_row("daily_price_crawl_hose", dt1, dt1_end, "success"),
            self._make_row("daily_indicator_compute_triggered", dt2, dt2_end, "success"),
        ]
        mock_session.execute = AsyncMock(return_value=mock_result)

        svc = HealthService(mock_session)
        result = await svc.get_pipeline_timeline(days=7)

        assert result[0]["total_seconds"] == 420.0

    @pytest.mark.asyncio
    async def test_empty_result(self, mock_session):
        """Returns empty list when no executions found."""
        from app.services.health_service import HealthService

        mock_result = MagicMock()
        mock_result.fetchall.return_value = []
        mock_session.execute = AsyncMock(return_value=mock_result)

        svc = HealthService(mock_session)
        result = await svc.get_pipeline_timeline(days=7)

        assert result == []

    @pytest.mark.asyncio
    async def test_vietnamese_job_names(self, mock_session):
        """Jobs use Vietnamese names from _JOB_NAMES_VN mapping."""
        from app.services.health_service import HealthService

        dt1 = datetime(2026, 4, 17, 8, 0, 0, tzinfo=timezone.utc)
        dt1_end = datetime(2026, 4, 17, 8, 5, 0, tzinfo=timezone.utc)

        mock_result = MagicMock()
        mock_result.fetchall.return_value = [
            self._make_row("daily_price_crawl_hose", dt1, dt1_end, "success"),
        ]
        mock_session.execute = AsyncMock(return_value=mock_result)

        svc = HealthService(mock_session)
        result = await svc.get_pipeline_timeline(days=7)

        step = result[0]["steps"][0]
        assert step["job_name"] == "Crawl giá HOSE"


# ---- API Endpoint Tests ----

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


SAMPLE_RUNS = [
    {
        "date": "2026-04-17",
        "total_seconds": 420.0,
        "steps": [
            {
                "job_id": "daily_price_crawl_hose",
                "job_name": "Crawl giá HOSE",
                "started_at": "2026-04-17T08:00:00+00:00",
                "duration_seconds": 300.0,
                "status": "success",
            },
            {
                "job_id": "daily_indicator_compute_triggered",
                "job_name": "Tính chỉ báo KT",
                "started_at": "2026-04-17T08:10:00+00:00",
                "duration_seconds": 120.0,
                "status": "success",
            },
        ],
    },
]


class TestPipelineTimelineEndpoint:
    """Tests for GET /health/pipeline-timeline."""

    def test_returns_200_with_runs(self, client):
        """GET /health/pipeline-timeline returns 200 with runs."""
        factory, _ = mock_async_session()
        with patch("app.api.health.async_session", factory), \
             patch("app.services.health_service.HealthService.get_pipeline_timeline",
                   new_callable=AsyncMock, return_value=SAMPLE_RUNS):
            resp = client.get("/api/health/pipeline-timeline")
        assert resp.status_code == 200
        data = resp.json()
        assert "runs" in data
        assert len(data["runs"]) == 1
        assert data["runs"][0]["date"] == "2026-04-17"
        assert len(data["runs"][0]["steps"]) == 2

    def test_default_days_7(self, client):
        """Default days parameter is 7."""
        factory, _ = mock_async_session()
        with patch("app.api.health.async_session", factory), \
             patch("app.services.health_service.HealthService.get_pipeline_timeline",
                   new_callable=AsyncMock, return_value=[]) as mock_method:
            resp = client.get("/api/health/pipeline-timeline")
        assert resp.status_code == 200
        mock_method.assert_called_once_with(days=7)

    def test_days_param_passed(self, client):
        """Custom days parameter is passed to service."""
        factory, _ = mock_async_session()
        with patch("app.api.health.async_session", factory), \
             patch("app.services.health_service.HealthService.get_pipeline_timeline",
                   new_callable=AsyncMock, return_value=[]) as mock_method:
            resp = client.get("/api/health/pipeline-timeline?days=14")
        assert resp.status_code == 200
        mock_method.assert_called_once_with(days=14)

    def test_days_capped_at_30(self, client):
        """days parameter capped at 30."""
        factory, _ = mock_async_session()
        with patch("app.api.health.async_session", factory), \
             patch("app.services.health_service.HealthService.get_pipeline_timeline",
                   new_callable=AsyncMock, return_value=[]) as mock_method:
            resp = client.get("/api/health/pipeline-timeline?days=60")
        assert resp.status_code == 200
        mock_method.assert_called_once_with(days=30)

    def test_empty_result(self, client):
        """Returns empty runs when no data."""
        factory, _ = mock_async_session()
        with patch("app.api.health.async_session", factory), \
             patch("app.services.health_service.HealthService.get_pipeline_timeline",
                   new_callable=AsyncMock, return_value=[]):
            resp = client.get("/api/health/pipeline-timeline")
        assert resp.status_code == 200
        assert resp.json()["runs"] == []

    def test_response_schema_structure(self, client):
        """Response matches PipelineTimelineResponse schema."""
        factory, _ = mock_async_session()
        with patch("app.api.health.async_session", factory), \
             patch("app.services.health_service.HealthService.get_pipeline_timeline",
                   new_callable=AsyncMock, return_value=SAMPLE_RUNS):
            resp = client.get("/api/health/pipeline-timeline")
        data = resp.json()
        run = data["runs"][0]
        assert "date" in run
        assert "total_seconds" in run
        assert "steps" in run
        step = run["steps"][0]
        assert "job_id" in step
        assert "job_name" in step
        assert "started_at" in step
        assert "duration_seconds" in step
        assert "status" in step
