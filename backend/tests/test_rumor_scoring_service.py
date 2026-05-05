"""Tests for RumorScoringService — prompt building, Gemini integration, upsert storage."""
import asyncio
import json
import pytest
from datetime import date, datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from app.schemas.rumor import RumorBatchResponse, RumorDirection, TickerRumorScore
from app.services.rumor_scoring_service import RumorScoringService


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_rumor_row(
    id=1,
    content="VNM sắp chia cổ tức 2000đ/cp cuối tháng",
    author_name="trader1",
    is_authentic=True,
    total_likes=25,
    total_replies=8,
    posted_at=None,
):
    """Create a mock DB row matching SELECT columns order:
    (id, content, author_name, is_authentic, total_likes, total_replies, posted_at)
    """
    if posted_at is None:
        posted_at = datetime(2025, 7, 21, 14, 0, 0, tzinfo=timezone.utc)
    # Use a tuple-like SimpleNamespace that supports index access
    row = (id, content, author_name, is_authentic, total_likes, total_replies, posted_at)
    return row


def _make_ticker_score(
    ticker="VNM",
    credibility=7,
    impact=6,
    direction="bullish",
    key_claims=None,
    reasoning="Nguồn đáng tin cậy, nhiều likes.",
):
    return TickerRumorScore(
        ticker=ticker,
        credibility_score=credibility,
        impact_score=impact,
        direction=direction,
        key_claims=key_claims or ["Chia cổ tức 2000đ/cp"],
        reasoning=reasoning,
    )


def _make_batch_response(ticker="VNM"):
    return RumorBatchResponse(scores=[_make_ticker_score(ticker=ticker)])


def _make_gemini_response(batch: RumorBatchResponse | None = None):
    """Mock Gemini API response with .parsed and .text."""
    if batch is None:
        batch = _make_batch_response()
    resp = MagicMock()
    resp.parsed = batch
    resp.text = batch.model_dump_json()
    resp.usage_metadata = MagicMock(total_token_count=100)
    return resp


@pytest.fixture
def mock_session():
    session = AsyncMock()
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    return session


@pytest.fixture
def service(mock_session):
    """Create RumorScoringService with mocked dependencies."""
    with patch("app.services.rumor_scoring_service.genai") as mock_genai:
        mock_genai.Client.return_value = MagicMock()
        with patch("app.services.rumor_scoring_service.settings") as mock_settings:
            mock_settings.gemini_api_key = "test-key"
            mock_settings.gemini_model = "gemini-2.5-flash-lite"
            mock_settings.gemini_batch_size = 8
            mock_settings.gemini_delay_seconds = 0  # No delay in tests
            svc = RumorScoringService(mock_session)
    return svc


# ---------------------------------------------------------------------------
# Test _build_prompt
# ---------------------------------------------------------------------------


class TestBuildPrompt:
    """Test prompt building with engagement metrics."""

    def test_build_prompt_includes_engagement_metrics(self, service):
        """Verified post shows [Xác thực ✓ | ...] bracket format matching few-shot."""
        row = _make_rumor_row(is_authentic=True, total_likes=25, total_replies=8)
        prompt = service._build_prompt("VNM", [row])

        assert "[Xác thực ✓ | 25 likes | 8 replies]" in prompt

    def test_build_prompt_regular_user(self, service):
        """Non-verified post shows [Thường | ...] bracket format."""
        row = _make_rumor_row(is_authentic=False, total_likes=2, total_replies=0)
        prompt = service._build_prompt("VNM", [row])

        assert "[Thường | 2 likes | 0 replies]" in prompt
        # The generated post line should not contain the verified tag
        post_lines = [l for l in prompt.split("\n") if l.startswith("1. [")]
        assert any("Thường" in l for l in post_lines)
        assert not any("Xác thực ✓ | 2 likes" in l for l in post_lines)

    def test_build_prompt_vietnamese_content(self, service):
        """Vietnamese content is preserved in prompt without mangling."""
        content = "HPG đang tích lũy vùng đáy, kỳ vọng tăng trưởng Q3"
        row = _make_rumor_row(content=content)
        prompt = service._build_prompt("HPG", [row])

        assert content in prompt
        assert "HPG" in prompt

    def test_build_prompt_truncates_long_content(self, service):
        """Content exceeding 500 chars is truncated to mitigate prompt injection."""
        long_content = "A" * 600
        row = _make_rumor_row(content=long_content)
        prompt = service._build_prompt("VNM", [row])

        assert "A" * 500 in prompt
        assert "A" * 501 not in prompt

    def test_build_prompt_includes_ticker_header(self, service):
        """Prompt includes ticker symbol and post count."""
        rows = [
            _make_rumor_row(id=1, content="Bài 1"),
            _make_rumor_row(id=2, content="Bài 2"),
        ]
        prompt = service._build_prompt("FPT", rows)

        assert "FPT (2 bài đăng)" in prompt

    def test_build_prompt_includes_few_shot(self, service):
        """Prompt starts with few-shot example from rumor_prompts."""
        row = _make_rumor_row()
        prompt = service._build_prompt("VNM", [row])

        assert "Ví dụ phân tích:" in prompt


# ---------------------------------------------------------------------------
# Test score_ticker
# ---------------------------------------------------------------------------


class TestScoreTicker:
    """Test score_ticker Gemini call, lock, and storage."""

    @pytest.mark.asyncio
    async def test_score_ticker_success(self, service, mock_session):
        """Happy path: Gemini returns valid response, score stored."""
        rumor_row = _make_rumor_row()
        gemini_resp = _make_gemini_response()

        # Mock DB: SELECT rumors returns rows
        select_result = MagicMock()
        select_result.fetchall.return_value = [rumor_row]

        # First call = SELECT rumors, second call = INSERT upsert
        mock_session.execute = AsyncMock(side_effect=[select_result, MagicMock()])

        with patch.object(
            service.gemini_client, "_call_gemini", new_callable=AsyncMock, return_value=gemini_resp
        ), patch.object(
            service.gemini_client, "_record_usage", new_callable=AsyncMock
        ):
            result = await service.score_ticker(1, "VNM")

        assert result is not None
        assert result.ticker == "VNM"
        assert result.credibility_score == 7
        assert result.impact_score == 6
        assert result.direction == RumorDirection.BULLISH
        # Verify upsert was called (second execute call)
        assert mock_session.execute.call_count == 2
        mock_session.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_score_ticker_skips_empty(self, service, mock_session):
        """Ticker with 0 rumors returns None, no Gemini call."""
        select_result = MagicMock()
        select_result.fetchall.return_value = []
        mock_session.execute = AsyncMock(return_value=select_result)

        with patch.object(
            service.gemini_client, "_call_gemini", new_callable=AsyncMock
        ) as mock_gemini:
            result = await service.score_ticker(1, "VNM")

        assert result is None
        mock_gemini.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_score_ticker_acquires_lock(self, service, mock_session):
        """Verify _gemini_lock is acquired during Gemini call."""
        rumor_row = _make_rumor_row()
        gemini_resp = _make_gemini_response()

        select_result = MagicMock()
        select_result.fetchall.return_value = [rumor_row]
        mock_session.execute = AsyncMock(side_effect=[select_result, MagicMock()])

        # Use a real lock to verify acquisition
        real_lock = asyncio.Lock()
        lock_acquired = False
        original_call_gemini = AsyncMock(return_value=gemini_resp)

        async def track_lock_call(*args, **kwargs):
            nonlocal lock_acquired
            lock_acquired = real_lock.locked()
            return gemini_resp

        with patch(
            "app.services.rumor_scoring_service._gemini_lock", real_lock
        ), patch.object(
            service.gemini_client, "_call_gemini", side_effect=track_lock_call
        ), patch.object(
            service.gemini_client, "_record_usage", new_callable=AsyncMock
        ):
            await service.score_ticker(1, "VNM")

        assert lock_acquired, "_gemini_lock was not acquired during Gemini call"


# ---------------------------------------------------------------------------
# Test _store_score
# ---------------------------------------------------------------------------


class TestStoreScore:
    """Test upsert storage pattern."""

    @pytest.mark.asyncio
    async def test_store_score_upsert(self, service, mock_session):
        """Store score uses INSERT ON CONFLICT DO UPDATE SQL."""
        score = _make_ticker_score()

        await service._store_score(1, score, [100, 101, 102])

        # Verify execute was called with upsert SQL
        call_args = mock_session.execute.call_args
        sql_text = str(call_args[0][0].text)
        assert "INSERT INTO rumor_scores" in sql_text
        assert "ON CONFLICT ON CONSTRAINT uq_rumor_scores_ticker_date" in sql_text
        assert "DO UPDATE SET" in sql_text
        mock_session.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_store_score_params(self, service, mock_session):
        """Upsert passes correct parameter values."""
        score = _make_ticker_score(
            credibility=9, impact=8, direction="bearish",
            key_claims=["Lợi nhuận giảm", "Nợ tăng"],
            reasoning="Nhiều tin tiêu cực."
        )

        await service._store_score(42, score, [200, 201])

        call_args = mock_session.execute.call_args
        params = call_args[0][1]
        assert params["tid"] == 42
        assert params["cred"] == 9
        assert params["impact"] == 8
        assert params["dir"] == "bearish"
        assert "Lợi nhuận giảm" in params["claims"]
        assert params["reasoning"] == "Nhiều tin tiêu cực."
        assert json.loads(params["pids"]) == [200, 201]


# ---------------------------------------------------------------------------
# Test score_all_tickers
# ---------------------------------------------------------------------------


class TestScoreAllTickers:
    """Test batch scoring orchestration."""

    @pytest.mark.asyncio
    async def test_score_all_tickers_skips_already_scored(self, service, mock_session):
        """Tickers already scored today are not returned by _get_tickers_with_unscored_rumors."""
        # Mock _get_tickers_with_unscored_rumors returning empty (all scored)
        with patch.object(
            service, "_get_tickers_with_unscored_rumors",
            new_callable=AsyncMock, return_value=[]
        ):
            results = await service.score_all_tickers()

        assert results == {}

    @pytest.mark.asyncio
    async def test_score_all_tickers_processes_multiple(self, service, mock_session):
        """Multiple tickers are scored, results mapped by symbol."""
        tickers = [(1, "VNM"), (2, "FPT")]
        score_vnm = _make_ticker_score(ticker="VNM")
        score_fpt = _make_ticker_score(ticker="FPT")

        with patch.object(
            service, "_get_tickers_with_unscored_rumors",
            new_callable=AsyncMock, return_value=tickers
        ), patch.object(
            service, "score_ticker",
            new_callable=AsyncMock, side_effect=[score_vnm, score_fpt]
        ):
            results = await service.score_all_tickers()

        assert results == {"VNM": True, "FPT": True}
