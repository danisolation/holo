"""Tests for APScheduler configuration and job functions."""
import pytest
from unittest.mock import patch, AsyncMock, MagicMock


class TestSchedulerManager:

    def test_scheduler_has_correct_timezone(self):
        """Scheduler must use Asia/Ho_Chi_Minh timezone."""
        from app.scheduler.manager import scheduler
        assert str(scheduler.timezone) == "Asia/Ho_Chi_Minh"

    def test_configure_jobs_registers_three_jobs(self):
        """configure_jobs must register daily, weekly ticker, weekly financial jobs."""
        from app.scheduler.manager import scheduler, configure_jobs

        # Remove any existing jobs first
        scheduler.remove_all_jobs()
        configure_jobs()

        job_ids = [job.id for job in scheduler.get_jobs()]
        assert "daily_price_crawl" in job_ids
        assert "weekly_ticker_refresh" in job_ids
        assert "weekly_financial_crawl" in job_ids
        assert len(job_ids) == 3

        # Clean up
        scheduler.remove_all_jobs()

    def test_daily_crawl_schedule(self):
        """Daily crawl must be Mon-Fri at configured hour:minute."""
        from app.scheduler.manager import scheduler, configure_jobs
        from app.config import settings

        scheduler.remove_all_jobs()
        configure_jobs()

        job = scheduler.get_job("daily_price_crawl")
        assert job is not None
        trigger = job.trigger

        # CronTrigger fields contain the schedule
        # Verify it has the expected time (from config: 15:30)
        assert str(settings.daily_crawl_hour) in str(trigger)
        assert str(settings.daily_crawl_minute) in str(trigger)

        scheduler.remove_all_jobs()


class TestJobFunctions:

    @pytest.mark.asyncio
    async def test_daily_price_crawl_calls_service(self):
        """daily_price_crawl job must call PriceService.crawl_daily."""
        with patch("app.scheduler.jobs.async_session") as mock_session_factory:
            mock_session = AsyncMock()
            mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=False)

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
        """weekly_ticker_refresh job must call TickerService.fetch_and_sync_tickers."""
        with patch("app.scheduler.jobs.async_session") as mock_session_factory:
            mock_session = AsyncMock()
            mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=False)

            with patch("app.scheduler.jobs.TickerService") as MockTickerService:
                mock_service = AsyncMock()
                mock_service.fetch_and_sync_tickers = AsyncMock(return_value={"synced": 400, "deactivated": 0, "total": 400})
                MockTickerService.return_value = mock_service

                from app.scheduler.jobs import weekly_ticker_refresh
                await weekly_ticker_refresh()

                MockTickerService.assert_called_once()
                mock_service.fetch_and_sync_tickers.assert_called_once()

    @pytest.mark.asyncio
    async def test_weekly_financial_crawl_calls_service(self):
        """weekly_financial_crawl job must call FinancialService.crawl_financials."""
        with patch("app.scheduler.jobs.async_session") as mock_session_factory:
            mock_session = AsyncMock()
            mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=False)

            with patch("app.scheduler.jobs.FinancialService") as MockFinancialService:
                mock_service = AsyncMock()
                mock_service.crawl_financials = AsyncMock(return_value={"success": 10, "failed": 0, "failed_symbols": []})
                MockFinancialService.return_value = mock_service

                from app.scheduler.jobs import weekly_financial_crawl
                await weekly_financial_crawl()

                MockFinancialService.assert_called_once()
                mock_service.crawl_financials.assert_called_once_with(period="quarter")
