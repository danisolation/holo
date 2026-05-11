"""Tests for tiered AI analysis (MKT-04) and on-demand endpoint."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class TestAnalyzeSingleTicker:

    @pytest.mark.asyncio
    async def test_analyze_single_ticker_runs_unified_only(self, mock_db_session):
        """analyze_single_ticker must run only unified analysis (not all 6 types)."""
        from app.services.ai_analysis_service import AIAnalysisService

        service = AIAnalysisService.__new__(AIAnalysisService)
        service.session = mock_db_session

        with (
            patch.object(service, "run_unified_analysis", new_callable=AsyncMock) as mock_unified,
            patch.object(service, "run_technical_analysis", new_callable=AsyncMock) as mock_tech,
            patch.object(service, "run_fundamental_analysis", new_callable=AsyncMock) as mock_fund,
            patch.object(service, "run_sentiment_analysis", new_callable=AsyncMock) as mock_sent,
            patch.object(service, "run_combined_analysis", new_callable=AsyncMock) as mock_comb,
            patch.object(service, "_crawl_and_score_rumors", new_callable=AsyncMock) as mock_crawl,
        ):
            mock_unified.return_value = {"success": 1, "failed": 0}
            mock_crawl.return_value = 5

            result = await service.analyze_single_ticker(ticker_id=1, symbol="AAA")

            # Only unified should be called
            mock_unified.assert_called_once_with(ticker_filter={"AAA": 1})
            mock_crawl.assert_called_once_with(1, "AAA")

            # Individual analysis types should NOT be called
            mock_tech.assert_not_called()
            mock_fund.assert_not_called()
            mock_sent.assert_not_called()
            mock_comb.assert_not_called()

            # Result should have unified + rumors_crawled
            assert "unified" in result
            assert result["rumors_crawled"] == 5


class TestOnDemandEndpoint:

    def test_analyze_now_returns_200(self):
        """POST /analysis/{symbol}/analyze-now must return 200."""
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
                    client = TestClient(app)

                    with patch("app.api.analysis.async_session") as mock_session_ctx:
                        mock_session = AsyncMock()
                        mock_session_ctx.return_value.__aenter__ = AsyncMock(return_value=mock_session)
                        mock_session_ctx.return_value.__aexit__ = AsyncMock(return_value=False)

                        # Mock ticker lookup (1st execute) and cooldown check (2nd execute)
                        mock_ticker = MagicMock()
                        mock_ticker.id = 1
                        mock_ticker.symbol = "AAA"
                        mock_ticker_result = MagicMock()
                        mock_ticker_result.scalar_one_or_none.return_value = mock_ticker
                        mock_cooldown_result = MagicMock()
                        mock_cooldown_result.scalar_one_or_none.return_value = None  # no recent analysis
                        mock_session.execute = AsyncMock(
                            side_effect=[mock_ticker_result, mock_cooldown_result]
                        )

                        response = client.post("/api/analysis/AAA/analyze-now")
                        assert response.status_code == 200
                        data = response.json()
                        assert data["triggered"] is True

    def test_analyze_now_returns_404_for_unknown_ticker(self):
        """POST /analysis/{symbol}/analyze-now must return 404 for unknown ticker."""
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
                    client = TestClient(app)

                    with patch("app.api.analysis.async_session") as mock_session_ctx:
                        mock_session = AsyncMock()
                        mock_session_ctx.return_value.__aenter__ = AsyncMock(return_value=mock_session)
                        mock_session_ctx.return_value.__aexit__ = AsyncMock(return_value=False)

                        # Mock ticker NOT found
                        mock_result = MagicMock()
                        mock_result.scalar_one_or_none.return_value = None
                        mock_session.execute = AsyncMock(return_value=mock_result)

                        response = client.post("/api/analysis/ZZZZZ/analyze-now")
                        assert response.status_code == 404
