"""Tests for Gemini API usage tracking (Phase 15-01).

Tests cover:
- GeminiUsage model field types and defaults
- GeminiUsageService record, daily, and today aggregation
- GET /health/gemini-usage API endpoint
"""
import pytest
from datetime import datetime, date, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from sqlalchemy import BigInteger, Integer, String
from sqlalchemy.types import TIMESTAMP


# ---- T-15-01: Model Tests ----

class TestGeminiUsageModel:
    """Verify GeminiUsage model fields and types."""

    def test_model_has_all_columns(self):
        """Model must have all required columns."""
        from app.models.gemini_usage import GeminiUsage
        columns = GeminiUsage.__table__.columns
        expected = [
            "id", "analysis_type", "batch_size", "prompt_tokens",
            "completion_tokens", "total_tokens", "model_name", "created_at",
        ]
        actual = [c.name for c in columns]
        for col_name in expected:
            assert col_name in actual, f"Missing column: {col_name}"

    def test_id_is_biginteger_pk(self):
        """ID must be BigInteger primary key."""
        from app.models.gemini_usage import GeminiUsage
        col = GeminiUsage.__table__.columns["id"]
        assert col.primary_key
        assert isinstance(col.type, BigInteger)

    def test_analysis_type_is_string30(self):
        """analysis_type must be String(30)."""
        from app.models.gemini_usage import GeminiUsage
        col = GeminiUsage.__table__.columns["analysis_type"]
        assert isinstance(col.type, String)
        assert col.type.length == 30

    def test_token_columns_are_integer(self):
        """prompt_tokens, completion_tokens, total_tokens must be Integer."""
        from app.models.gemini_usage import GeminiUsage
        for name in ["prompt_tokens", "completion_tokens", "total_tokens"]:
            col = GeminiUsage.__table__.columns[name]
            assert isinstance(col.type, Integer), f"{name} should be Integer"

    def test_batch_size_is_integer(self):
        """batch_size must be Integer."""
        from app.models.gemini_usage import GeminiUsage
        col = GeminiUsage.__table__.columns["batch_size"]
        assert isinstance(col.type, Integer)

    def test_model_name_is_string50(self):
        """model_name must be String(50)."""
        from app.models.gemini_usage import GeminiUsage
        col = GeminiUsage.__table__.columns["model_name"]
        assert isinstance(col.type, String)
        assert col.type.length == 50

    def test_created_at_is_timestamp_with_tz(self):
        """created_at must be TIMESTAMP with timezone and server default."""
        from app.models.gemini_usage import GeminiUsage
        col = GeminiUsage.__table__.columns["created_at"]
        assert isinstance(col.type, TIMESTAMP)
        assert col.type.timezone is True
        assert col.server_default is not None

    def test_tablename(self):
        """Table name should be gemini_usage."""
        from app.models.gemini_usage import GeminiUsage
        assert GeminiUsage.__tablename__ == "gemini_usage"

    def test_model_registered_in_init(self):
        """GeminiUsage must be importable from app.models."""
        from app.models import GeminiUsage
        assert GeminiUsage.__tablename__ == "gemini_usage"


# ---- T-15-02: Service Tests ----

class TestGeminiUsageServiceRecord:
    """Tests for GeminiUsageService.record_usage."""

    @pytest.fixture
    def mock_session(self):
        session = AsyncMock()
        session.add = MagicMock()
        session.flush = AsyncMock()
        return session

    @pytest.fixture
    def usage_metadata(self):
        meta = MagicMock()
        meta.prompt_token_count = 150
        meta.candidates_token_count = 350
        meta.total_token_count = 500
        return meta

    @pytest.mark.asyncio
    async def test_record_usage_inserts_row(self, mock_session, usage_metadata):
        """record_usage should add a GeminiUsage object to session."""
        from app.services.gemini_usage_service import GeminiUsageService
        svc = GeminiUsageService(mock_session)
        await svc.record_usage(
            analysis_type="technical",
            batch_size=10,
            usage_metadata=usage_metadata,
            model_name="gemini-2.0-flash",
        )
        mock_session.add.assert_called_once()
        usage_obj = mock_session.add.call_args[0][0]
        assert usage_obj.analysis_type == "technical"
        assert usage_obj.batch_size == 10
        assert usage_obj.prompt_tokens == 150
        assert usage_obj.completion_tokens == 350
        assert usage_obj.total_tokens == 500
        assert usage_obj.model_name == "gemini-2.0-flash"

    @pytest.mark.asyncio
    async def test_record_usage_handles_none_metadata(self, mock_session):
        """record_usage should handle None usage_metadata gracefully."""
        from app.services.gemini_usage_service import GeminiUsageService
        svc = GeminiUsageService(mock_session)
        await svc.record_usage(
            analysis_type="technical",
            batch_size=10,
            usage_metadata=None,
            model_name="gemini-2.0-flash",
        )
        # Should still add but with 0 tokens
        mock_session.add.assert_called_once()
        usage_obj = mock_session.add.call_args[0][0]
        assert usage_obj.prompt_tokens == 0
        assert usage_obj.completion_tokens == 0
        assert usage_obj.total_tokens == 0


class TestGeminiUsageServiceDailyAggregation:
    """Tests for GeminiUsageService.get_daily_usage."""

    @pytest.mark.asyncio
    async def test_get_daily_usage_returns_list(self):
        """get_daily_usage should return a list of daily aggregates."""
        from app.services.gemini_usage_service import GeminiUsageService

        # Mock session with execute returning rows
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.all.return_value = [
            MagicMock(date=date(2026, 4, 17), total_tokens=5000, total_requests=10),
            MagicMock(date=date(2026, 4, 16), total_tokens=3000, total_requests=6),
        ]
        mock_session.execute = AsyncMock(return_value=mock_result)

        svc = GeminiUsageService(mock_session)
        result = await svc.get_daily_usage(days=7)
        assert isinstance(result, list)
        assert len(result) == 2
        assert result[0]["date"] == "2026-04-17"
        assert result[0]["tokens"] == 5000
        assert result[0]["requests"] == 10

    @pytest.mark.asyncio
    async def test_get_daily_usage_empty(self):
        """get_daily_usage with no data returns empty list."""
        from app.services.gemini_usage_service import GeminiUsageService

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.all.return_value = []
        mock_session.execute = AsyncMock(return_value=mock_result)

        svc = GeminiUsageService(mock_session)
        result = await svc.get_daily_usage(days=7)
        assert result == []


class TestGeminiUsageServiceTodayUsage:
    """Tests for GeminiUsageService.get_today_usage."""

    @pytest.mark.asyncio
    async def test_get_today_usage_returns_dict(self):
        """get_today_usage should return a dict with today's totals + breakdown."""
        from app.services.gemini_usage_service import GeminiUsageService

        mock_session = AsyncMock()

        # First query: per-type breakdown
        mock_breakdown_result = MagicMock()
        mock_breakdown_result.all.return_value = [
            MagicMock(analysis_type="technical", total_tokens=3000, total_requests=5),
            MagicMock(analysis_type="fundamental", total_tokens=2000, total_requests=3),
        ]
        mock_session.execute = AsyncMock(return_value=mock_breakdown_result)

        svc = GeminiUsageService(mock_session)
        result = await svc.get_today_usage()
        assert "requests" in result
        assert "tokens" in result
        assert "breakdown" in result
        assert isinstance(result["breakdown"], list)

    @pytest.mark.asyncio
    async def test_get_today_usage_zero_when_empty(self):
        """get_today_usage with no data returns zeros."""
        from app.services.gemini_usage_service import GeminiUsageService

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.all.return_value = []
        mock_session.execute = AsyncMock(return_value=mock_result)

        svc = GeminiUsageService(mock_session)
        result = await svc.get_today_usage()
        assert result["requests"] == 0
        assert result["tokens"] == 0
        assert result["breakdown"] == []


# ---- T-15-02: AI Service Integration Test ----

class TestAIServiceRecordsUsage:
    """Test that AIAnalysisService calls record_usage after Gemini calls."""

    @pytest.mark.asyncio
    async def test_technical_batch_records_usage(self):
        """_analyze_technical_batch should call record_usage after success."""
        with patch("app.services.ai_analysis_service.settings") as mock_settings, \
             patch("app.services.ai_analysis_service.genai") as mock_genai, \
             patch("app.services.ai_analysis_service.GeminiUsageService") as MockUsageSvc:

            mock_settings.gemini_api_key = "test-key"
            mock_settings.gemini_model = "gemini-2.0-flash"
            mock_settings.gemini_batch_size = 10
            mock_settings.gemini_delay_seconds = 0

            # Mock usage metadata
            mock_usage = MagicMock()
            mock_usage.prompt_token_count = 100
            mock_usage.candidates_token_count = 200
            mock_usage.total_token_count = 300

            # Mock response
            mock_response = MagicMock()
            mock_response.usage_metadata = mock_usage
            mock_response.parsed = MagicMock()
            mock_response.parsed.results = []
            mock_response.text = '{"results": []}'

            # Mock usage service
            mock_usage_svc_instance = AsyncMock()
            MockUsageSvc.return_value = mock_usage_svc_instance

            mock_session = AsyncMock()
            from app.services.ai_analysis_service import AIAnalysisService
            svc = AIAnalysisService(mock_session, api_key="test-key")

            # Patch _call_gemini and _build_technical_prompt to bypass prompt building
            svc._call_gemini = AsyncMock(return_value=mock_response)
            svc._build_technical_prompt = MagicMock(return_value="test prompt")
            await svc._analyze_technical_batch({"VNM": {}})

            mock_usage_svc_instance.record_usage.assert_called_once()
            call_kwargs = mock_usage_svc_instance.record_usage.call_args
            assert call_kwargs.kwargs["analysis_type"] == "technical"
            assert call_kwargs.kwargs["batch_size"] == 1
            assert call_kwargs.kwargs["model_name"] == "gemini-2.0-flash"


# ---- T-15-03: API Endpoint Tests ----

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


class TestGeminiUsageEndpoint:
    """Tests for GET /health/gemini-usage."""

    SAMPLE_TODAY = {
        "requests": 15,
        "tokens": 50000,
        "breakdown": [
            {"analysis_type": "technical", "requests": 8, "tokens": 30000},
            {"analysis_type": "fundamental", "requests": 7, "tokens": 20000},
        ],
    }
    SAMPLE_DAILY = [
        {"date": "2026-04-17", "tokens": 50000, "requests": 15},
        {"date": "2026-04-16", "tokens": 30000, "requests": 10},
    ]

    def test_gemini_usage_returns_200(self, client):
        """GET /health/gemini-usage returns 200 with valid schema."""
        factory, _ = mock_async_session()
        with patch("app.api.health.async_session", factory), \
             patch("app.services.gemini_usage_service.GeminiUsageService.get_today_usage",
                   new_callable=AsyncMock, return_value=self.SAMPLE_TODAY), \
             patch("app.services.gemini_usage_service.GeminiUsageService.get_daily_usage",
                   new_callable=AsyncMock, return_value=self.SAMPLE_DAILY):
            resp = client.get("/api/health/gemini-usage")
        assert resp.status_code == 200
        data = resp.json()
        assert "today" in data
        assert "daily" in data
        assert data["today"]["limit_requests"] == 1500
        assert data["today"]["limit_tokens"] == 1_000_000

    def test_gemini_usage_zero_data(self, client):
        """Endpoint returns zeros when no usage data exists."""
        factory, _ = mock_async_session()
        empty_today = {"requests": 0, "tokens": 0, "breakdown": []}
        with patch("app.api.health.async_session", factory), \
             patch("app.services.gemini_usage_service.GeminiUsageService.get_today_usage",
                   new_callable=AsyncMock, return_value=empty_today), \
             patch("app.services.gemini_usage_service.GeminiUsageService.get_daily_usage",
                   new_callable=AsyncMock, return_value=[]):
            resp = client.get("/api/health/gemini-usage")
        assert resp.status_code == 200
        data = resp.json()
        assert data["today"]["requests"] == 0
        assert data["today"]["tokens"] == 0
        assert data["daily"] == []

    def test_gemini_usage_days_param(self, client):
        """days query parameter is passed correctly."""
        factory, _ = mock_async_session()
        with patch("app.api.health.async_session", factory), \
             patch("app.services.gemini_usage_service.GeminiUsageService.get_today_usage",
                   new_callable=AsyncMock, return_value={"requests": 0, "tokens": 0, "breakdown": []}) as mock_today, \
             patch("app.services.gemini_usage_service.GeminiUsageService.get_daily_usage",
                   new_callable=AsyncMock, return_value=[]) as mock_daily:
            resp = client.get("/api/health/gemini-usage?days=14")
        assert resp.status_code == 200
        mock_daily.assert_called_once_with(days=14)

    def test_gemini_usage_days_max_30(self, client):
        """days parameter capped at 30."""
        factory, _ = mock_async_session()
        with patch("app.api.health.async_session", factory), \
             patch("app.services.gemini_usage_service.GeminiUsageService.get_today_usage",
                   new_callable=AsyncMock, return_value={"requests": 0, "tokens": 0, "breakdown": []}) as mock_today, \
             patch("app.services.gemini_usage_service.GeminiUsageService.get_daily_usage",
                   new_callable=AsyncMock, return_value=[]) as mock_daily:
            resp = client.get("/api/health/gemini-usage?days=60")
        assert resp.status_code == 200
        # Should be capped to 30
        mock_daily.assert_called_once_with(days=30)

    def test_gemini_usage_response_schema(self, client):
        """Response matches GeminiUsageResponse schema structure."""
        factory, _ = mock_async_session()
        with patch("app.api.health.async_session", factory), \
             patch("app.services.gemini_usage_service.GeminiUsageService.get_today_usage",
                   new_callable=AsyncMock, return_value=self.SAMPLE_TODAY), \
             patch("app.services.gemini_usage_service.GeminiUsageService.get_daily_usage",
                   new_callable=AsyncMock, return_value=self.SAMPLE_DAILY):
            resp = client.get("/api/health/gemini-usage")
        data = resp.json()
        today = data["today"]
        assert "requests" in today
        assert "tokens" in today
        assert "limit_requests" in today
        assert "limit_tokens" in today
        assert "breakdown" in today
        for item in today["breakdown"]:
            assert "analysis_type" in item
            assert "requests" in item
            assert "tokens" in item
        for day in data["daily"]:
            assert "date" in day
            assert "tokens" in day
            assert "requests" in day
