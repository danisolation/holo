"""Tests for Telegram bot module: formatter, alert service, and scheduler integration."""
import pytest
from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch


class TestMessageFormatter:
    """Tests for MessageFormatter output."""

    def test_welcome_contains_all_commands(self):
        from app.telegram.formatter import MessageFormatter
        msg = MessageFormatter.welcome()
        assert "/watch" in msg
        assert "/unwatch" in msg
        assert "/list" in msg
        assert "/check" in msg
        assert "/alert" in msg
        assert "/summary" in msg
        assert "Holo" in msg

    def test_watch_added_contains_symbol(self):
        from app.telegram.formatter import MessageFormatter
        msg = MessageFormatter.watch_added("VNM")
        assert "VNM" in msg
        assert "✅" in msg

    def test_ticker_not_found(self):
        from app.telegram.formatter import MessageFormatter
        msg = MessageFormatter.ticker_not_found("XYZ")
        assert "XYZ" in msg
        assert "❌" in msg

    def test_watchlist_empty(self):
        from app.telegram.formatter import MessageFormatter
        msg = MessageFormatter.watchlist([])
        assert "trống" in msg

    def test_watchlist_with_items(self):
        from app.telegram.formatter import MessageFormatter
        items = [
            {"symbol": "VNM", "signal": "mua", "score": 8, "close": 85000.0},
            {"symbol": "FPT", "signal": "giu", "score": 6, "close": 120000.0},
        ]
        msg = MessageFormatter.watchlist(items)
        assert "VNM" in msg
        assert "FPT" in msg
        assert "85,000" in msg

    def test_ticker_summary_format(self):
        from app.telegram.formatter import MessageFormatter
        data = {
            "symbol": "VNM",
            "name": "Vinamilk",
            "close": 85000.0,
            "change_pct": 2.5,
            "volume": 1000000,
            "technical_signal": "buy",
            "technical_score": 7,
            "combined_signal": "mua",
            "combined_score": 8,
            "combined_reasoning": "Kỹ thuật tốt, cơ bản vững",
        }
        msg = MessageFormatter.ticker_summary(data)
        assert "VNM" in msg
        assert "Vinamilk" in msg
        assert "85,000" in msg
        assert "mua" in msg.lower() or "MUA" in msg

    def test_alert_created_up(self):
        from app.telegram.formatter import MessageFormatter
        msg = MessageFormatter.alert_created("VNM", Decimal("90000"), "up")
        assert "VNM" in msg
        assert "90,000" in msg
        assert "vượt lên" in msg

    def test_alert_created_down(self):
        from app.telegram.formatter import MessageFormatter
        msg = MessageFormatter.alert_created("VNM", Decimal("80000"), "down")
        assert "giảm xuống" in msg

    def test_alert_triggered_format(self):
        from app.telegram.formatter import MessageFormatter
        msg = MessageFormatter.alert_triggered("VNM", Decimal("91000"), Decimal("90000"), "up")
        assert "CẢNH BÁO GIÁ" in msg
        assert "VNM" in msg
        assert "91,000" in msg

    def test_signal_change_format(self):
        from app.telegram.formatter import MessageFormatter
        msg = MessageFormatter.signal_change("VNM", "giu", "mua", 8, "Xu hướng tăng mạnh")
        assert "VNM" in msg
        assert "giu" in msg
        assert "MUA" in msg or "mua" in msg
        assert "8/10" in msg

    def test_daily_summary_format(self):
        from app.telegram.formatter import MessageFormatter
        data = {
            "date": "2025-07-18",
            "top_movers": [
                {"symbol": "VNM", "close": 85000, "change_pct": 5.2},
                {"symbol": "FPT", "close": 120000, "change_pct": -3.1},
            ],
            "watchlist_changes": [
                {"symbol": "VNM", "old_signal": "giu", "new_signal": "mua"},
            ],
            "new_recommendations": [
                {"symbol": "VIC", "signal": "mua", "score": 9},
            ],
            "total_tickers": 400,
            "analyzed_count": 380,
        }
        msg = MessageFormatter.daily_summary(data)
        assert "2025-07-18" in msg
        assert "VNM" in msg
        assert "5.2%" in msg or "+5.2%" in msg
        assert "VIC" in msg

    def test_signal_emoji_mapping(self):
        from app.telegram.formatter import MessageFormatter
        assert MessageFormatter._signal_emoji("mua") == "🟢"
        assert MessageFormatter._signal_emoji("ban") == "🔴"
        assert MessageFormatter._signal_emoji("giu") == "🟡"
        assert MessageFormatter._signal_emoji("neutral") == "🟡"
        assert MessageFormatter._signal_emoji("") == "⚪"

    def test_usage_error(self):
        from app.telegram.formatter import MessageFormatter
        msg = MessageFormatter.usage_error("/watch", "/watch VNM")
        assert "Sai cú pháp" in msg
        assert "/watch VNM" in msg


class TestAlertService:
    """Tests for AlertService logic using mocked database."""

    @pytest.mark.asyncio
    async def test_check_signal_changes_no_chat_id(self):
        """Should return 0 if no chat_id configured."""
        from app.telegram.services import AlertService
        session = AsyncMock()
        service = AlertService(session)

        with patch("app.telegram.services.settings") as mock_settings:
            mock_settings.telegram_chat_id = ""
            result = await service.check_signal_changes(chat_id="")
            assert result == 0

    @pytest.mark.asyncio
    async def test_check_price_alerts_no_chat_id(self):
        """Should return 0 if no chat_id configured."""
        from app.telegram.services import AlertService
        session = AsyncMock()
        service = AlertService(session)

        with patch("app.telegram.services.settings") as mock_settings:
            mock_settings.telegram_chat_id = ""
            result = await service.check_price_alerts(chat_id="")
            assert result == 0

    @pytest.mark.asyncio
    async def test_build_daily_summary_returns_dict(self):
        """Summary should return a dict with expected keys."""
        from app.telegram.services import AlertService

        # Mock session that returns empty results
        session = AsyncMock()
        mock_result = MagicMock()
        mock_result.all.return_value = []
        mock_result.scalar_one_or_none.return_value = None
        session.execute = AsyncMock(return_value=mock_result)

        service = AlertService(session)

        with patch("app.telegram.services.settings") as mock_settings:
            mock_settings.telegram_chat_id = "12345"
            result = await service.build_daily_summary()

        assert "date" in result
        assert "top_movers" in result
        assert "watchlist_changes" in result
        assert "new_recommendations" in result
        assert isinstance(result["top_movers"], list)


class TestTelegramBot:
    """Tests for TelegramBot class."""

    def test_bot_not_configured_without_token(self):
        """Bot should report not configured when token is empty."""
        from app.telegram.bot import TelegramBot
        with patch("app.telegram.bot.settings") as mock_settings:
            mock_settings.telegram_bot_token = ""
            mock_settings.telegram_chat_id = "12345"
            bot = TelegramBot()
            assert not bot.is_configured

    def test_bot_not_configured_without_chat_id(self):
        """Bot should report not configured when chat_id is empty."""
        from app.telegram.bot import TelegramBot
        with patch("app.telegram.bot.settings") as mock_settings:
            mock_settings.telegram_bot_token = "fake-token"
            mock_settings.telegram_chat_id = ""
            bot = TelegramBot()
            assert not bot.is_configured

    def test_bot_configured_with_both(self):
        """Bot should report configured when both token and chat_id are set."""
        from app.telegram.bot import TelegramBot
        with patch("app.telegram.bot.settings") as mock_settings:
            mock_settings.telegram_bot_token = "fake-token"
            mock_settings.telegram_chat_id = "12345"
            bot = TelegramBot()
            assert bot.is_configured

    @pytest.mark.asyncio
    async def test_send_message_fails_when_not_configured(self):
        """send_message should return False when not configured."""
        from app.telegram.bot import TelegramBot
        with patch("app.telegram.bot.settings") as mock_settings:
            mock_settings.telegram_bot_token = ""
            mock_settings.telegram_chat_id = ""
            bot = TelegramBot()
            result = await bot.send_message("test")
            assert result is False


class TestSchedulerChaining:
    """Tests for Phase 4 job chaining in scheduler manager."""

    def test_configure_jobs_registers_summary_cron(self):
        """configure_jobs should register daily_summary_send job."""
        from app.scheduler.manager import scheduler, configure_jobs

        scheduler.remove_all_jobs()
        scheduler._listeners = []
        configure_jobs()

        job_ids = [job.id for job in scheduler.get_jobs()]
        assert "daily_summary_send" in job_ids
        assert "daily_price_crawl" in job_ids  # existing job still present

        scheduler.remove_all_jobs()
        scheduler._listeners = []

    def test_combined_chains_to_signal_alerts(self):
        """After combined analysis completes, signal alert check should be triggered."""
        from app.scheduler.manager import _on_job_executed
        from apscheduler import events as aps_events

        mock_event = MagicMock(spec=aps_events.JobExecutionEvent)
        mock_event.exception = None
        mock_event.job_id = "daily_combined_triggered"

        with patch("app.scheduler.manager.scheduler") as mock_scheduler:
            _on_job_executed(mock_event)
            # Verify add_job was called with signal alert check
            calls = mock_scheduler.add_job.call_args_list
            job_ids = [call.kwargs.get("id", "") or call[1].get("id", "") for call in calls]
            assert "daily_signal_alert_check_triggered" in job_ids

    def test_price_crawl_chains_to_both_indicators_and_price_alerts(self):
        """After price crawl, both indicator compute AND price alert check should trigger."""
        from app.scheduler.manager import _on_job_executed
        from apscheduler import events as aps_events

        mock_event = MagicMock(spec=aps_events.JobExecutionEvent)
        mock_event.exception = None
        mock_event.job_id = "daily_price_crawl"

        with patch("app.scheduler.manager.scheduler") as mock_scheduler:
            _on_job_executed(mock_event)
            calls = mock_scheduler.add_job.call_args_list
            job_ids = [call.kwargs.get("id", "") or call[1].get("id", "") for call in calls]
            assert "daily_indicator_compute_triggered" in job_ids
            assert "daily_price_alert_check_triggered" in job_ids

    def test_failed_job_does_not_chain(self):
        """Jobs that failed should not trigger chaining."""
        from app.scheduler.manager import _on_job_executed
        from apscheduler import events as aps_events

        mock_event = MagicMock(spec=aps_events.JobExecutionEvent)
        mock_event.exception = Exception("Job failed")
        mock_event.job_id = "daily_combined_triggered"

        with patch("app.scheduler.manager.scheduler") as mock_scheduler:
            _on_job_executed(mock_event)
            mock_scheduler.add_job.assert_not_called()


class TestHandlerRegistration:
    """Tests for command handler registration."""

    def test_register_handlers_adds_all_commands(self):
        """register_handlers should add 7 command handlers."""
        from app.telegram.handlers import register_handlers

        mock_app = MagicMock()
        register_handlers(mock_app)

        assert mock_app.add_handler.call_count == 7
        # Extract command names from the CommandHandler objects
        commands = []
        for call in mock_app.add_handler.call_args_list:
            handler = call[0][0]
            if hasattr(handler, "commands"):
                commands.extend(handler.commands)
        expected = {"start", "watch", "unwatch", "list", "check", "alert", "summary"}
        assert set(commands) == expected
