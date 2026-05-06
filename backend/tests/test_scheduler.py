"""Tests for APScheduler configuration and job functions."""
import pytest
from unittest.mock import patch, AsyncMock, MagicMock


def _mock_job_svc():
    """Create a mock JobExecutionService for job function tests."""
    mock_svc = MagicMock()
    mock_execution = MagicMock()
    mock_execution.status = "running"
    mock_svc.start = AsyncMock(return_value=mock_execution)
    mock_svc.complete = AsyncMock()
    mock_svc.fail = AsyncMock()
    return mock_svc


class TestSchedulerManager:

    def test_scheduler_has_correct_timezone(self):
        """Scheduler must use Asia/Ho_Chi_Minh timezone."""
        from app.scheduler.manager import scheduler
        assert str(scheduler.timezone) == "Asia/Ho_Chi_Minh"

    def test_configure_jobs_registers_nine_jobs(self):
        """configure_jobs must register all expected jobs.

        With vndirect_ws_enabled=True (default), VCI polling jobs are skipped (7 jobs).
        With vndirect_ws_enabled=False, all 9 jobs are registered.
        """
        from app.scheduler.manager import scheduler, configure_jobs
        from app.config import settings

        # Remove any existing jobs first
        scheduler.remove_all_jobs()
        scheduler._listeners = []
        configure_jobs()

        job_ids = [job.id for job in scheduler.get_jobs()]
        assert "daily_price_crawl_hose" in job_ids
        assert "weekly_ticker_refresh" in job_ids
        assert "weekly_financial_crawl" in job_ids
        assert "weekly_behavior_analysis" in job_ids
        assert "create_weekly_risk_prompt" in job_ids
        assert "generate_weekly_review" in job_ids
        assert "morning_price_crawl_hose" in job_ids

        if settings.vndirect_ws_enabled:
            # VCI polling jobs skipped when VNDirect WS is active
            assert "realtime_price_poll" not in job_ids
            assert "realtime_heartbeat" not in job_ids
            assert len(job_ids) == 7
        else:
            assert "realtime_price_poll" in job_ids
            assert "realtime_heartbeat" in job_ids
            assert len(job_ids) == 9

        # Clean up
        scheduler.remove_all_jobs()
        scheduler._listeners = []

    def test_daily_crawl_schedule(self):
        """Daily HOSE crawl must be Mon-Fri at 15:30."""
        from app.scheduler.manager import scheduler, configure_jobs

        scheduler.remove_all_jobs()
        scheduler._listeners = []
        configure_jobs()

        job = scheduler.get_job("daily_price_crawl_hose")
        assert job is not None
        trigger = job.trigger

        # Verify HOSE crawl at 15:30
        assert "15" in str(trigger)
        assert "30" in str(trigger)

        scheduler.remove_all_jobs()
        scheduler._listeners = []


class TestJobFunctions:

    @pytest.mark.asyncio
    async def test_daily_price_crawl_calls_service(self):
        """daily_price_crawl job must call PriceService.crawl_daily."""
        with patch("app.scheduler.jobs.async_session") as mock_session_factory:
            mock_session = AsyncMock()
            mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=False)

            with patch("app.scheduler.jobs.JobExecutionService") as MockJobSvc:
                MockJobSvc.return_value = _mock_job_svc()

                with patch("app.scheduler.jobs.PriceService") as MockPriceService:
                    mock_service = AsyncMock()
                    mock_service.crawl_daily = AsyncMock(return_value={"success": 10, "failed": 0, "skipped": 0, "failed_symbols": []})
                    MockPriceService.return_value = mock_service

                    from app.scheduler.jobs import daily_price_crawl
                    await daily_price_crawl()

                    MockPriceService.assert_called_once()
                    mock_service.crawl_daily.assert_called_once()

    @pytest.mark.asyncio
    async def test_weekly_ticker_refresh_calls_service(self):
        """weekly_ticker_refresh job must call TickerService.fetch_and_sync_tickers for HOSE only."""
        with patch("app.scheduler.jobs.async_session") as mock_session_factory:
            mock_session = AsyncMock()
            mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=False)

            with patch("app.scheduler.jobs.JobExecutionService") as MockJobSvc:
                MockJobSvc.return_value = _mock_job_svc()

                with patch("app.scheduler.jobs.TickerService") as MockTickerService:
                    mock_service = AsyncMock()
                    mock_service.fetch_and_sync_tickers = AsyncMock(return_value={"synced": 400, "deactivated": 0, "total": 400})
                    MockTickerService.return_value = mock_service

                    from app.scheduler.jobs import weekly_ticker_refresh
                    await weekly_ticker_refresh()

                    MockTickerService.assert_called_once()
                    # Now syncs HOSE only
                    assert mock_service.fetch_and_sync_tickers.call_count == 1

    @pytest.mark.asyncio
    async def test_weekly_financial_crawl_calls_service(self):
        """weekly_financial_crawl job must call FinancialService.crawl_financials."""
        with patch("app.scheduler.jobs.async_session") as mock_session_factory:
            mock_session = AsyncMock()
            mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=False)

            with patch("app.scheduler.jobs.JobExecutionService") as MockJobSvc:
                MockJobSvc.return_value = _mock_job_svc()

                with patch("app.scheduler.jobs.FinancialService") as MockFinancialService:
                    mock_service = AsyncMock()
                    mock_service.crawl_financials = AsyncMock(return_value={"success": 10, "failed": 0, "failed_symbols": []})
                    MockFinancialService.return_value = mock_service

                    from app.scheduler.jobs import weekly_financial_crawl
                    await weekly_financial_crawl()

                    MockFinancialService.assert_called_once()
                    mock_service.crawl_financials.assert_called_once_with(period="quarter")


class TestJobChaining:
    """Tests for EVENT_JOB_EXECUTED job chaining (Phase 2)."""

    def test_on_job_executed_chains_indicators_after_price_crawl(self):
        """Successful daily_price_crawl_hose must trigger daily_indicator_compute."""
        from app.scheduler.manager import _on_job_executed, scheduler

        mock_event = MagicMock()
        mock_event.job_id = "daily_price_crawl_hose"
        mock_event.exception = None

        with patch.object(scheduler, "add_job") as mock_add:
            _on_job_executed(mock_event)
            assert mock_add.call_count == 1
            call_ids = [call.kwargs.get("id", "") or call[1].get("id", "") for call in mock_add.call_args_list]
            assert "daily_indicator_compute_triggered" in call_ids

    def test_on_job_executed_chains_discovery_after_indicators(self):
        """Successful daily_indicator_compute must trigger daily_discovery_scoring."""
        from app.scheduler.manager import _on_job_executed, scheduler

        mock_event = MagicMock()
        mock_event.job_id = "daily_indicator_compute_triggered"
        mock_event.exception = None

        with patch.object(scheduler, "add_job") as mock_add:
            _on_job_executed(mock_event)
            mock_add.assert_called_once()
            call_kwargs = mock_add.call_args
            assert call_kwargs.kwargs.get("id") == "daily_discovery_scoring_triggered" or \
                   call_kwargs[1].get("id") == "daily_discovery_scoring_triggered"

    def test_on_job_executed_skips_on_failure(self):
        """Failed jobs must NOT trigger the next job in the chain."""
        from app.scheduler.manager import _on_job_executed, scheduler

        mock_event = MagicMock()
        mock_event.job_id = "daily_price_crawl_hose"
        mock_event.exception = Exception("crawl failed")

        with patch.object(scheduler, "add_job") as mock_add:
            _on_job_executed(mock_event)
            mock_add.assert_not_called()

    def test_configure_jobs_still_registers_original_jobs(self):
        """configure_jobs must register the HOSE crawl plus weekly jobs."""
        from app.scheduler.manager import scheduler, configure_jobs

        scheduler.remove_all_jobs()
        # Remove any existing listeners
        scheduler._listeners = []

        configure_jobs()

        job_ids = [job.id for job in scheduler.get_jobs()]
        assert "daily_price_crawl_hose" in job_ids
        assert "weekly_ticker_refresh" in job_ids
        assert "weekly_financial_crawl" in job_ids

        scheduler.remove_all_jobs()
        scheduler._listeners = []


class TestNewJobFunctions:
    """Tests for Phase 2 job functions."""

    @pytest.mark.asyncio
    async def test_daily_indicator_compute_calls_service(self):
        """daily_indicator_compute must call IndicatorService.compute_all_tickers."""
        with patch("app.scheduler.jobs.async_session") as mock_session_factory:
            mock_session = AsyncMock()
            mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=False)

            with patch("app.scheduler.jobs.JobExecutionService") as MockJobSvc:
                MockJobSvc.return_value = _mock_job_svc()

                with patch("app.services.indicator_service.IndicatorService") as MockService:
                    mock_svc = AsyncMock()
                    mock_svc.compute_all_tickers = AsyncMock(return_value={"success": 400, "failed": 0, "skipped": 0, "failed_symbols": []})
                    MockService.return_value = mock_svc

                    from app.scheduler.jobs import daily_indicator_compute
                    await daily_indicator_compute()

                    mock_svc.compute_all_tickers.assert_called_once()

    @pytest.mark.asyncio
    async def test_daily_ai_analysis_calls_service(self):
        """daily_ai_analysis must call AIAnalysisService.analyze_all_tickers."""
        with patch("app.scheduler.jobs.async_session") as mock_session_factory:
            mock_session = AsyncMock()
            mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=False)

            with patch("app.scheduler.jobs.JobExecutionService") as MockJobSvc:
                MockJobSvc.return_value = _mock_job_svc()

                with patch("app.scheduler.jobs._get_watchlist_ticker_map", new_callable=AsyncMock, return_value={"VNM": 1, "FPT": 2}):
                    with patch("app.services.ai_analysis_service.AIAnalysisService") as MockService:
                        mock_svc = AsyncMock()
                        mock_svc.analyze_all_tickers = AsyncMock(return_value={"technical": {"success": 400, "failed": 0, "failed_symbols": []}})
                        MockService.return_value = mock_svc

                        from app.scheduler.jobs import daily_ai_analysis
                        await daily_ai_analysis()

                        mock_svc.analyze_all_tickers.assert_called_once_with(analysis_type="both", ticker_filter={"VNM": 1, "FPT": 2})


class TestPhase3Chaining:
    """Tests for Phase 3 job chaining: AI → news → sentiment → combined."""

    def test_on_job_executed_chains_news_after_ai(self):
        """Successful daily_ai_analysis must trigger daily_news_crawl."""
        from app.scheduler.manager import _on_job_executed, scheduler

        mock_event = MagicMock()
        mock_event.job_id = "daily_ai_analysis_triggered"
        mock_event.exception = None

        with patch.object(scheduler, "add_job") as mock_add:
            _on_job_executed(mock_event)
            mock_add.assert_called_once()
            call_kwargs = mock_add.call_args
            assert call_kwargs.kwargs.get("id") == "daily_news_crawl_triggered" or \
                   call_kwargs[1].get("id") == "daily_news_crawl_triggered"

    def test_on_job_executed_chains_sentiment_after_news(self):
        """Successful daily_news_crawl must trigger daily_sentiment_analysis."""
        from app.scheduler.manager import _on_job_executed, scheduler

        mock_event = MagicMock()
        mock_event.job_id = "daily_news_crawl_triggered"
        mock_event.exception = None

        with patch.object(scheduler, "add_job") as mock_add:
            _on_job_executed(mock_event)
            mock_add.assert_called_once()
            call_kwargs = mock_add.call_args
            assert call_kwargs.kwargs.get("id") == "daily_sentiment_triggered" or \
                   call_kwargs[1].get("id") == "daily_sentiment_triggered"

    def test_on_job_executed_chains_combined_after_sentiment(self):
        """Successful daily_sentiment must trigger daily_combined_analysis."""
        from app.scheduler.manager import _on_job_executed, scheduler

        mock_event = MagicMock()
        mock_event.job_id = "daily_sentiment_triggered"
        mock_event.exception = None

        with patch.object(scheduler, "add_job") as mock_add:
            _on_job_executed(mock_event)
            mock_add.assert_called_once()
            call_kwargs = mock_add.call_args
            assert call_kwargs.kwargs.get("id") == "daily_combined_triggered" or \
                   call_kwargs[1].get("id") == "daily_combined_triggered"

    def test_on_job_executed_manual_ai_also_chains_news(self):
        """Manual daily_ai_analysis must also chain to news crawl."""
        from app.scheduler.manager import _on_job_executed, scheduler

        mock_event = MagicMock()
        mock_event.job_id = "daily_ai_analysis_manual"
        mock_event.exception = None

        with patch.object(scheduler, "add_job") as mock_add:
            _on_job_executed(mock_event)
            mock_add.assert_called_once()

    def test_on_job_executed_failed_news_does_not_chain(self):
        """Failed news crawl must NOT trigger sentiment analysis."""
        from app.scheduler.manager import _on_job_executed, scheduler

        mock_event = MagicMock()
        mock_event.job_id = "daily_news_crawl_triggered"
        mock_event.exception = Exception("CafeF down")

        with patch.object(scheduler, "add_job") as mock_add:
            _on_job_executed(mock_event)
            mock_add.assert_not_called()


class TestPhase3JobFunctions:
    """Tests for Phase 3 job functions."""

    @pytest.mark.asyncio
    async def test_daily_news_crawl_calls_service(self):
        """daily_news_crawl must call CafeFCrawler.crawl_all_tickers."""
        with patch("app.scheduler.jobs.async_session") as mock_session_factory:
            mock_session = AsyncMock()
            mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=False)

            with patch("app.scheduler.jobs.JobExecutionService") as MockJobSvc:
                MockJobSvc.return_value = _mock_job_svc()

                with patch("app.scheduler.jobs.TickerService") as MockTickerSvc:
                    mock_ticker_svc = AsyncMock()
                    mock_ticker_svc.get_ticker_id_map = AsyncMock(return_value={"VNM": 1, "FPT": 2})
                    MockTickerSvc.return_value = mock_ticker_svc

                    with patch("app.crawlers.cafef_crawler.CafeFCrawler") as MockCrawler:
                        mock_crawler = AsyncMock()
                        mock_crawler.crawl_all_tickers = AsyncMock(return_value={"success": 400, "failed": 0, "total_articles": 100, "failed_symbols": []})
                        MockCrawler.return_value = mock_crawler

                        from app.scheduler.jobs import daily_news_crawl
                        await daily_news_crawl()

                        MockCrawler.assert_called_once()
                        mock_crawler.crawl_all_tickers.assert_called_once()

    @pytest.mark.asyncio
    async def test_daily_sentiment_calls_service(self):
        """daily_sentiment_analysis must call AIAnalysisService.analyze_all_tickers('sentiment')."""
        with patch("app.scheduler.jobs.async_session") as mock_session_factory:
            mock_session = AsyncMock()
            mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=False)

            with patch("app.scheduler.jobs.JobExecutionService") as MockJobSvc:
                MockJobSvc.return_value = _mock_job_svc()

                with patch("app.scheduler.jobs._get_watchlist_ticker_map", new_callable=AsyncMock, return_value={"VNM": 1, "FPT": 2}):
                    with patch("app.services.ai_analysis_service.AIAnalysisService") as MockService:
                        mock_svc = AsyncMock()
                        mock_svc.analyze_all_tickers = AsyncMock(return_value={"sentiment": {"success": 400, "failed": 0, "failed_symbols": []}})
                        MockService.return_value = mock_svc

                        from app.scheduler.jobs import daily_sentiment_analysis
                        await daily_sentiment_analysis()

                        mock_svc.analyze_all_tickers.assert_called_once_with(analysis_type="sentiment", ticker_filter={"VNM": 1, "FPT": 2})

    @pytest.mark.asyncio
    async def test_daily_combined_calls_service(self):
        """daily_combined_analysis must call AIAnalysisService.analyze_all_tickers('combined')."""
        with patch("app.scheduler.jobs.async_session") as mock_session_factory:
            mock_session = AsyncMock()
            mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=False)

            with patch("app.scheduler.jobs.JobExecutionService") as MockJobSvc:
                MockJobSvc.return_value = _mock_job_svc()

                with patch("app.scheduler.jobs._get_watchlist_ticker_map", new_callable=AsyncMock, return_value={"VNM": 1, "FPT": 2}):
                    with patch("app.services.ai_analysis_service.AIAnalysisService") as MockService:
                        mock_svc = AsyncMock()
                        mock_svc.analyze_all_tickers = AsyncMock(return_value={"combined": {"success": 400, "failed": 0, "failed_symbols": []}})
                        MockService.return_value = mock_svc

                        from app.scheduler.jobs import daily_combined_analysis
                        await daily_combined_analysis()

                        mock_svc.analyze_all_tickers.assert_called_once_with(analysis_type="combined", ticker_filter={"VNM": 1, "FPT": 2})
