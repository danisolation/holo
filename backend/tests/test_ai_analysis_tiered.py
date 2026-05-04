"""Tests for tiered AI analysis (MKT-04) and on-demand endpoint."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class TestAnalyzeSingleTicker:

    @pytest.mark.asyncio
    async def test_analyze_single_ticker_calls_all_types(self, mock_db_session):
        """analyze_single_ticker must call all 4 run_*_analysis methods under the lock."""
        from app.services.ai_analysis_service import AIAnalysisService

        service = AIAnalysisService.__new__(AIAnalysisService)
        service.session = mock_db_session

        with (
            patch.object(service, "run_technical_analysis", new_callable=AsyncMock) as mock_tech,
            patch.object(service, "run_fundamental_analysis", new_callable=AsyncMock) as mock_fund,
            patch.object(service, "run_sentiment_analysis", new_callable=AsyncMock) as mock_sent,
            patch.object(service, "run_combined_analysis", new_callable=AsyncMock) as mock_comb,
        ):
            mock_tech.return_value = {"success": 1, "failed": 0}
            mock_fund.return_value = {"success": 1, "failed": 0}
            mock_sent.return_value = {"success": 1, "failed": 0}
            mock_comb.return_value = {"success": 1, "failed": 0}

            result = await service.analyze_single_ticker(ticker_id=1, symbol="AAA")

            # All 4 methods should be called once each
            mock_tech.assert_called_once()
            mock_fund.assert_called_once()
            mock_sent.assert_called_once()
            mock_comb.assert_called_once()

            # Each should receive the ticker_filter
            expected_filter = {"AAA": 1}
            mock_tech.assert_called_with(ticker_filter=expected_filter)
            mock_fund.assert_called_with(ticker_filter=expected_filter)
            mock_sent.assert_called_with(ticker_filter=expected_filter)
            mock_comb.assert_called_with(ticker_filter=expected_filter)

            # Result should have all 4 types
            assert "technical" in result
            assert "fundamental" in result
            assert "sentiment" in result
            assert "combined" in result


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
