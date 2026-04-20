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
        assert "daily_price_crawl_hose" in job_ids  # staggered exchange crawl

        scheduler.remove_all_jobs()
        scheduler._listeners = []

    def test_combined_chains_to_trading_signal(self):
        """After combined analysis completes, trading signal analysis should be triggered (Phase 19)."""
        from app.scheduler.manager import _on_job_executed
        from apscheduler import events as aps_events

        mock_event = MagicMock(spec=aps_events.JobExecutionEvent)
        mock_event.exception = None
        mock_event.job_id = "daily_combined_triggered"

        with patch("app.scheduler.manager.scheduler") as mock_scheduler:
            _on_job_executed(mock_event)
            # Verify add_job was called with trading signal analysis
            calls = mock_scheduler.add_job.call_args_list
            job_ids = [call.kwargs.get("id", "") or call[1].get("id", "") for call in calls]
            assert "daily_trading_signal_triggered" in job_ids

    def test_trading_signal_chains_to_signal_alerts(self):
        """After trading signal analysis completes, signal alert check + hnx_upcom should trigger (Phase 19)."""
        from app.scheduler.manager import _on_job_executed
        from apscheduler import events as aps_events

        mock_event = MagicMock(spec=aps_events.JobExecutionEvent)
        mock_event.exception = None
        mock_event.job_id = "daily_trading_signal_triggered"

        with patch("app.scheduler.manager.scheduler") as mock_scheduler:
            _on_job_executed(mock_event)
            calls = mock_scheduler.add_job.call_args_list
            job_ids = [call.kwargs.get("id", "") or call[1].get("id", "") for call in calls]
            assert "daily_signal_alert_check_triggered" in job_ids
            assert "daily_hnx_upcom_analysis_triggered" in job_ids

    def test_price_crawl_chains_to_both_indicators_and_price_alerts(self):
        """After UPCOM price crawl (last exchange), both indicator compute AND price alert check should trigger."""
        from app.scheduler.manager import _on_job_executed
        from apscheduler import events as aps_events

        mock_event = MagicMock(spec=aps_events.JobExecutionEvent)
        mock_event.exception = None
        mock_event.job_id = "daily_price_crawl_upcom"

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
        """register_handlers should add 11 command handlers."""
        from app.telegram.handlers import register_handlers

        mock_app = MagicMock()
        register_handlers(mock_app)

        assert mock_app.add_handler.call_count == 11
        # Extract command names from the CommandHandler objects
        commands = []
        for call in mock_app.add_handler.call_args_list:
            handler = call[0][0]
            if hasattr(handler, "commands"):
                commands.extend(handler.commands)
        expected = {"start", "watch", "unwatch", "list", "check", "alert", "summary", "buy", "sell", "portfolio", "pnl"}
        assert set(commands) == expected


class TestPortfolioFormatter:
    """Tests for portfolio-related MessageFormatter methods."""

    def test_trade_recorded_buy(self):
        from app.telegram.formatter import MessageFormatter
        trade = {"side": "BUY", "symbol": "VNM", "quantity": 100, "price": 85000.0,
                 "fees": 0.0, "realized_pnl": None}
        msg = MessageFormatter.trade_recorded(trade)
        assert "MUA" in msg
        assert "VNM" in msg
        assert "85,000" in msg
        assert "🟢" in msg
        assert "Lãi/Lỗ" not in msg

    def test_trade_recorded_sell_with_pnl(self):
        from app.telegram.formatter import MessageFormatter
        trade = {"side": "SELL", "symbol": "VNM", "quantity": 50, "price": 90000.0,
                 "fees": 0.0, "realized_pnl": 250000.0}
        msg = MessageFormatter.trade_recorded(trade)
        assert "BÁN" in msg
        assert "🔴" in msg
        assert "250,000" in msg
        assert "Lãi/Lỗ" in msg

    def test_trade_recorded_with_fees(self):
        from app.telegram.formatter import MessageFormatter
        trade = {"side": "BUY", "symbol": "VNM", "quantity": 100, "price": 85000.0,
                 "fees": 150000.0, "realized_pnl": None}
        msg = MessageFormatter.trade_recorded(trade)
        assert "Phí" in msg
        assert "150,000" in msg

    def test_portfolio_view_empty(self):
        from app.telegram.formatter import MessageFormatter
        msg = MessageFormatter.portfolio_view([], {})
        assert "Chưa có" in msg
        assert "/buy" in msg

    def test_portfolio_view_with_holdings(self):
        from app.telegram.formatter import MessageFormatter
        holdings = [
            {"symbol": "VNM", "quantity": 100, "avg_cost": 85000.0, "market_price": 90000.0,
             "market_value": 9000000.0, "total_cost": 8500000.0,
             "unrealized_pnl": 500000.0, "unrealized_pnl_pct": 5.88},
            {"symbol": "FPT", "quantity": 50, "avg_cost": 120000.0, "market_price": 115000.0,
             "market_value": 5750000.0, "total_cost": 6000000.0,
             "unrealized_pnl": -250000.0, "unrealized_pnl_pct": -4.17},
        ]
        summary = {"total_invested": 14500000.0, "total_market_value": 14750000.0,
                    "total_realized_pnl": 0.0, "total_unrealized_pnl": 250000.0,
                    "total_return_pct": 1.72, "holdings_count": 2}
        msg = MessageFormatter.portfolio_view(holdings, summary)
        assert "VNM" in msg
        assert "FPT" in msg
        assert "🟢" in msg
        assert "🔴" in msg

    def test_ticker_pnl_with_lots(self):
        from app.telegram.formatter import MessageFormatter
        data = {"symbol": "VNM", "name": "Vinamilk", "quantity": 100, "avg_cost": 85000.0,
                "market_price": 90000.0, "unrealized_pnl": 500000.0, "unrealized_pnl_pct": 5.88,
                "realized_pnl": 0.0,
                "lots": [
                    {"buy_date": "2024-01-10", "buy_price": 85000.0, "quantity": 100,
                     "remaining": 100, "lot_pnl": 500000.0, "lot_pnl_pct": 5.88},
                ]}
        msg = MessageFormatter.ticker_pnl(data)
        assert "VNM" in msg
        assert "2024-01-10" in msg
        assert "FIFO" in msg or "Lô" in msg
        assert "500,000" in msg

    def test_ticker_pnl_no_position(self):
        from app.telegram.formatter import MessageFormatter
        data = {"symbol": "VNM", "name": "Vinamilk", "quantity": 0,
                "avg_cost": 0, "market_price": None, "unrealized_pnl": None,
                "unrealized_pnl_pct": None, "realized_pnl": 0.0, "lots": []}
        msg = MessageFormatter.ticker_pnl(data)
        assert "Không có vị thế" in msg or "VNM" in msg

    def test_welcome_includes_portfolio_commands(self):
        from app.telegram.formatter import MessageFormatter
        msg = MessageFormatter.welcome()
        assert "/buy" in msg
        assert "/sell" in msg
        assert "/portfolio" in msg
        assert "/pnl" in msg


class TestPortfolioCommands:
    """Tests for /buy, /sell, /portfolio, /pnl command handlers."""

    def _make_update_context(self, args=None):
        """Create mock update and context for handler tests."""
        update = MagicMock()
        update.message = MagicMock()
        update.message.reply_text = AsyncMock()
        update.effective_chat.id = 12345
        context = MagicMock()
        context.args = args or []
        return update, context

    @pytest.mark.asyncio
    @patch("app.telegram.handlers.async_session")
    async def test_buy_records_trade(self, mock_session_factory):
        mock_session = AsyncMock()
        mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=False)

        update, context = self._make_update_context(["VNM", "100", "85000"])

        with patch("app.telegram.handlers.PortfolioService") as MockPS:
            mock_svc = MockPS.return_value
            mock_svc.record_trade = AsyncMock(return_value={
                "side": "BUY", "symbol": "VNM", "quantity": 100, "price": 85000.0,
                "fees": 0.0, "realized_pnl": None,
            })
            from app.telegram.handlers import buy_command
            await buy_command(update, context)
            mock_svc.record_trade.assert_called_once()
            call_kwargs = mock_svc.record_trade.call_args
            assert call_kwargs[1]["side"] == "BUY"
            assert call_kwargs[1]["symbol"] == "VNM"
            assert call_kwargs[1]["quantity"] == 100
            update.message.reply_text.assert_called_once()

    @pytest.mark.asyncio
    @patch("app.telegram.handlers.async_session")
    async def test_buy_with_fee(self, mock_session_factory):
        mock_session = AsyncMock()
        mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=False)

        update, context = self._make_update_context(["VNM", "100", "85000", "150000"])

        with patch("app.telegram.handlers.PortfolioService") as MockPS:
            mock_svc = MockPS.return_value
            mock_svc.record_trade = AsyncMock(return_value={
                "side": "BUY", "symbol": "VNM", "quantity": 100, "price": 85000.0,
                "fees": 150000.0, "realized_pnl": None,
            })
            from app.telegram.handlers import buy_command
            await buy_command(update, context)
            call_kwargs = mock_svc.record_trade.call_args[1]
            assert call_kwargs["fees"] == 150000.0

    @pytest.mark.asyncio
    async def test_buy_invalid_args_too_few(self):
        update, context = self._make_update_context(["VNM"])
        from app.telegram.handlers import buy_command
        await buy_command(update, context)
        msg = update.message.reply_text.call_args[0][0]
        assert "Sai cú pháp" in msg

    @pytest.mark.asyncio
    async def test_buy_invalid_args_non_numeric(self):
        update, context = self._make_update_context(["VNM", "abc", "85000"])
        from app.telegram.handlers import buy_command
        await buy_command(update, context)
        msg = update.message.reply_text.call_args[0][0]
        assert "Sai cú pháp" in msg

    @pytest.mark.asyncio
    @patch("app.telegram.handlers.async_session")
    async def test_buy_unknown_ticker(self, mock_session_factory):
        mock_session = AsyncMock()
        mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=False)

        update, context = self._make_update_context(["XYZ", "100", "85000"])

        with patch("app.telegram.handlers.PortfolioService") as MockPS:
            mock_svc = MockPS.return_value
            mock_svc.record_trade = AsyncMock(side_effect=ValueError("Ticker 'XYZ' not found"))
            from app.telegram.handlers import buy_command
            await buy_command(update, context)
            msg = update.message.reply_text.call_args[0][0]
            assert "Không tìm thấy" in msg or "XYZ" in msg

    @pytest.mark.asyncio
    @patch("app.telegram.handlers.async_session")
    async def test_sell_shows_pnl(self, mock_session_factory):
        mock_session = AsyncMock()
        mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=False)

        update, context = self._make_update_context(["VNM", "50", "90000"])

        with patch("app.telegram.handlers.PortfolioService") as MockPS:
            mock_svc = MockPS.return_value
            mock_svc.record_trade = AsyncMock(return_value={
                "side": "SELL", "symbol": "VNM", "quantity": 50, "price": 90000.0,
                "fees": 0.0, "realized_pnl": 250000.0,
            })
            from app.telegram.handlers import sell_command
            await sell_command(update, context)
            call_kwargs = mock_svc.record_trade.call_args[1]
            assert call_kwargs["side"] == "SELL"
            update.message.reply_text.assert_called_once()

    @pytest.mark.asyncio
    @patch("app.telegram.handlers.async_session")
    async def test_sell_exceeds_shares(self, mock_session_factory):
        mock_session = AsyncMock()
        mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=False)

        update, context = self._make_update_context(["VNM", "500", "90000"])

        with patch("app.telegram.handlers.PortfolioService") as MockPS:
            mock_svc = MockPS.return_value
            mock_svc.record_trade = AsyncMock(
                side_effect=ValueError("Cannot sell 500 shares — only 100 available"))
            from app.telegram.handlers import sell_command
            await sell_command(update, context)
            msg = update.message.reply_text.call_args[0][0]
            assert "Cannot sell" in msg or "⚠️" in msg

    @pytest.mark.asyncio
    @patch("app.telegram.handlers.async_session")
    async def test_portfolio_shows_holdings(self, mock_session_factory):
        mock_session = AsyncMock()
        mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=False)

        update, context = self._make_update_context()

        with patch("app.telegram.handlers.PortfolioService") as MockPS:
            mock_svc = MockPS.return_value
            mock_svc.get_holdings = AsyncMock(return_value=[
                {"symbol": "VNM", "quantity": 100, "avg_cost": 85000.0,
                 "market_price": 90000.0, "market_value": 9000000.0,
                 "total_cost": 8500000.0, "unrealized_pnl": 500000.0, "unrealized_pnl_pct": 5.88}
            ])
            mock_svc.get_summary = AsyncMock(return_value={
                "total_invested": 8500000.0, "total_market_value": 9000000.0,
                "total_realized_pnl": 0.0, "total_unrealized_pnl": 500000.0,
                "total_return_pct": 5.88, "holdings_count": 1,
            })
            from app.telegram.handlers import portfolio_command
            await portfolio_command(update, context)
            mock_svc.get_holdings.assert_called_once()
            mock_svc.get_summary.assert_called_once()
            update.message.reply_text.assert_called_once()

    @pytest.mark.asyncio
    @patch("app.telegram.handlers.async_session")
    async def test_portfolio_empty(self, mock_session_factory):
        mock_session = AsyncMock()
        mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=False)

        update, context = self._make_update_context()

        with patch("app.telegram.handlers.PortfolioService") as MockPS:
            mock_svc = MockPS.return_value
            mock_svc.get_holdings = AsyncMock(return_value=[])
            mock_svc.get_summary = AsyncMock(return_value={
                "total_invested": 0, "total_market_value": None,
                "total_realized_pnl": 0, "total_unrealized_pnl": None,
                "total_return_pct": None, "holdings_count": 0,
            })
            from app.telegram.handlers import portfolio_command
            await portfolio_command(update, context)
            msg = update.message.reply_text.call_args[0][0]
            assert "Chưa có" in msg

    @pytest.mark.asyncio
    @patch("app.telegram.handlers.async_session")
    async def test_pnl_shows_lots(self, mock_session_factory):
        mock_session = AsyncMock()
        mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=False)

        update, context = self._make_update_context(["VNM"])

        with patch("app.telegram.handlers.PortfolioService") as MockPS:
            mock_svc = MockPS.return_value
            mock_svc.get_ticker_pnl = AsyncMock(return_value={
                "symbol": "VNM", "name": "Vinamilk", "quantity": 100,
                "avg_cost": 85000.0, "market_price": 90000.0,
                "unrealized_pnl": 500000.0, "unrealized_pnl_pct": 5.88,
                "realized_pnl": 0.0,
                "lots": [{"buy_date": "2024-01-10", "buy_price": 85000.0,
                          "quantity": 100, "remaining": 100,
                          "lot_pnl": 500000.0, "lot_pnl_pct": 5.88}],
            })
            from app.telegram.handlers import pnl_command
            await pnl_command(update, context)
            update.message.reply_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_pnl_missing_args(self):
        update, context = self._make_update_context([])
        from app.telegram.handlers import pnl_command
        await pnl_command(update, context)
        msg = update.message.reply_text.call_args[0][0]
        assert "Sai cú pháp" in msg

    @pytest.mark.asyncio
    @patch("app.telegram.handlers.async_session")
    async def test_pnl_unknown_ticker(self, mock_session_factory):
        mock_session = AsyncMock()
        mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=False)

        update, context = self._make_update_context(["XYZ"])

        with patch("app.telegram.handlers.PortfolioService") as MockPS:
            mock_svc = MockPS.return_value
            mock_svc.get_ticker_pnl = AsyncMock(side_effect=ValueError("Ticker 'XYZ' not found"))
            from app.telegram.handlers import pnl_command
            await pnl_command(update, context)
            msg = update.message.reply_text.call_args[0][0]
            assert "Không tìm thấy" in msg or "XYZ" in msg


class TestDailySummaryPortfolio:
    """Tests for portfolio integration in daily summary."""

    def test_summary_includes_portfolio(self):
        from app.telegram.formatter import MessageFormatter
        data = {
            "date": "2024-01-15",
            "top_movers": [{"symbol": "VNM", "close": 85000.0, "change_pct": 2.5}],
            "watchlist_changes": [],
            "new_recommendations": [
                {"symbol": "VNM", "signal": "mua", "score": 8},
                {"symbol": "FPT", "signal": "mua", "score": 9},
            ],
            "total_tickers": 400, "analyzed_count": 400,
            "portfolio_holdings": [
                {"symbol": "VNM", "quantity": 100, "market_price": 85000.0,
                 "unrealized_pnl": 500000.0, "unrealized_pnl_pct": 5.88}
            ],
            "portfolio_summary": {"total_unrealized_pnl": 500000.0, "total_return_pct": 5.88},
            "owned_symbols": {"VNM"},
        }
        msg = MessageFormatter.daily_summary(data)
        assert "Danh mục của bạn" in msg
        assert "📌" in msg

    def test_summary_without_portfolio(self):
        from app.telegram.formatter import MessageFormatter
        data = {"date": "2024-01-15", "top_movers": [], "watchlist_changes": [],
                "new_recommendations": [], "total_tickers": 0, "analyzed_count": 0}
        msg = MessageFormatter.daily_summary(data)
        assert "Danh mục" not in msg

    def test_owned_tickers_first(self):
        from app.telegram.formatter import MessageFormatter
        data = {
            "date": "2024-01-15",
            "top_movers": [], "watchlist_changes": [],
            "new_recommendations": [
                {"symbol": "FPT", "signal": "mua", "score": 9},
                {"symbol": "VNM", "signal": "mua", "score": 8},
            ],
            "total_tickers": 400, "analyzed_count": 400,
            "owned_symbols": {"VNM"},
        }
        msg = MessageFormatter.daily_summary(data)
        # VNM should appear before FPT in recommendations section
        rec_start = msg.index("Khuyến nghị")
        vnm_pos = msg.index("VNM", rec_start)
        fpt_pos = msg.index("FPT", rec_start)
        assert vnm_pos < fpt_pos
        assert "📌" in msg

    def test_owned_tickers_no_recommendations(self):
        from app.telegram.formatter import MessageFormatter
        data = {
            "date": "2024-01-15",
            "top_movers": [], "watchlist_changes": [],
            "new_recommendations": [],
            "total_tickers": 400, "analyzed_count": 400,
            "owned_symbols": {"VNM"},
        }
        msg = MessageFormatter.daily_summary(data)
        assert "📌" not in msg

    @pytest.mark.asyncio
    async def test_build_daily_summary_fetches_portfolio(self):
        from app.telegram.services import AlertService

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.all.return_value = []
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)

        service = AlertService(mock_session)

        with patch("app.telegram.services.settings") as mock_settings, \
             patch("app.services.portfolio_service.PortfolioService") as MockPS:
            mock_settings.telegram_chat_id = "12345"
            mock_svc = MockPS.return_value
            mock_svc.get_holdings = AsyncMock(return_value=[
                {"symbol": "VNM", "quantity": 100, "market_price": 85000.0,
                 "unrealized_pnl": 500000.0, "unrealized_pnl_pct": 5.88}
            ])
            mock_svc.get_summary = AsyncMock(return_value={
                "total_unrealized_pnl": 500000.0, "total_return_pct": 5.88})
            result = await service.build_daily_summary()
            assert "portfolio_holdings" in result
            assert "owned_symbols" in result

    @pytest.mark.asyncio
    async def test_build_daily_summary_portfolio_failure_graceful(self):
        from app.telegram.services import AlertService

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.all.return_value = []
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)

        service = AlertService(mock_session)

        with patch("app.telegram.services.settings") as mock_settings, \
             patch("app.services.portfolio_service.PortfolioService") as MockPS:
            mock_settings.telegram_chat_id = "12345"
            MockPS.return_value.get_holdings = AsyncMock(side_effect=Exception("DB error"))
            result = await service.build_daily_summary()
            assert "portfolio_holdings" not in result
            assert "date" in result
