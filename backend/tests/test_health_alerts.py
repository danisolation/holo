"""Tests for health alert service + scheduler job (Phase 15-02, T-15-05).

Tests cover:
- Consecutive job failure detection (≥3 same job_id failed in 24h)
- Stale data detection (any source > 2× threshold)
- Cooldown prevents re-alerting within 4 hours
- Cooldown expires after 4 hours allowing new alert
- Vietnamese Telegram message format
- Scheduler job registration
"""
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch, call


# ---- HealthAlertService Tests ----

class TestConsecutiveFailureDetection:
    """Test detection of ≥3 consecutive failures for same job_id."""

    @pytest.fixture
    def mock_session(self):
        session = AsyncMock()
        session.execute = AsyncMock()
        return session

    def _make_failure_row(self, job_id, count):
        row = MagicMock()
        row.job_id = job_id
        row.fail_count = count
        return row

    @pytest.mark.asyncio
    async def test_detects_3_consecutive_failures(self, mock_session):
        """Alert fires when a job has ≥3 failures in last 24h."""
        from app.services.health_alert_service import HealthAlertService, _last_alert_times

        # Clear cooldowns
        _last_alert_times.clear()

        # Mock: failure query returns job with 3 failures
        mock_fail_result = MagicMock()
        mock_fail_result.fetchall.return_value = [
            self._make_failure_row("daily_price_crawl_hose", 3),
        ]
        # Mock: stale data returns no stale items
        mock_stale_items = []
        # Mock: pool is fine
        mock_pool = MagicMock()
        mock_pool.size.return_value = 5
        mock_pool.checkedout.return_value = 1

        mock_session.execute = AsyncMock(return_value=mock_fail_result)

        mock_telegram = AsyncMock()
        mock_telegram.is_configured = True
        mock_telegram.send_message = AsyncMock()

        with patch("app.services.health_alert_service.HealthService") as MockHS, \
             patch("app.services.health_alert_service.engine") as mock_engine, \
             patch("app.services.health_alert_service.telegram_bot", mock_telegram):
            mock_hs_instance = AsyncMock()
            mock_hs_instance.get_data_freshness = AsyncMock(return_value=mock_stale_items)
            MockHS.return_value = mock_hs_instance
            mock_engine.pool = mock_pool

            svc = HealthAlertService(mock_session)
            await svc.check_and_alert()

        # Should have sent alert for job failures
        mock_telegram.send_message.assert_called()

    @pytest.mark.asyncio
    async def test_no_alert_below_3_failures(self, mock_session):
        """No alert when failures < 3."""
        from app.services.health_alert_service import HealthAlertService, _last_alert_times

        _last_alert_times.clear()

        # Mock: failure query returns job with only 2 failures
        mock_fail_result = MagicMock()
        mock_fail_result.fetchall.return_value = [
            self._make_failure_row("daily_price_crawl_hose", 2),
        ]
        mock_stale_items = []
        mock_pool = MagicMock()
        mock_pool.size.return_value = 5
        mock_pool.checkedout.return_value = 1

        mock_session.execute = AsyncMock(return_value=mock_fail_result)

        mock_telegram = AsyncMock()
        mock_telegram.is_configured = True
        mock_telegram.send_message = AsyncMock()

        with patch("app.services.health_alert_service.HealthService") as MockHS, \
             patch("app.services.health_alert_service.engine") as mock_engine, \
             patch("app.services.health_alert_service.telegram_bot", mock_telegram):
            mock_hs_instance = AsyncMock()
            mock_hs_instance.get_data_freshness = AsyncMock(return_value=mock_stale_items)
            MockHS.return_value = mock_hs_instance
            mock_engine.pool = mock_pool

            svc = HealthAlertService(mock_session)
            await svc.check_and_alert()

        mock_telegram.send_message.assert_not_called()


class TestStaleDataDetection:
    """Test stale data detection triggers alert."""

    @pytest.fixture
    def mock_session(self):
        session = AsyncMock()
        session.execute = AsyncMock()
        return session

    @pytest.mark.asyncio
    async def test_stale_data_triggers_alert(self, mock_session):
        """Alert fires when any data source is stale beyond 2× threshold."""
        from app.services.health_alert_service import HealthAlertService, _last_alert_times

        _last_alert_times.clear()

        # No failure jobs
        mock_fail_result = MagicMock()
        mock_fail_result.fetchall.return_value = []
        mock_session.execute = AsyncMock(return_value=mock_fail_result)

        # Stale data: threshold is 48h, data is >96h old (2× threshold)
        mock_stale_items = [
            {
                "data_type": "Giá cổ phiếu",
                "table_name": "daily_prices",
                "latest": "2026-04-10T00:00:00",
                "is_stale": True,
                "threshold_hours": 48,
            },
        ]

        mock_pool = MagicMock()
        mock_pool.size.return_value = 5
        mock_pool.checkedout.return_value = 1

        mock_telegram = AsyncMock()
        mock_telegram.is_configured = True
        mock_telegram.send_message = AsyncMock()

        with patch("app.services.health_alert_service.HealthService") as MockHS, \
             patch("app.services.health_alert_service.engine") as mock_engine, \
             patch("app.services.health_alert_service.telegram_bot", mock_telegram):
            mock_hs_instance = AsyncMock()
            mock_hs_instance.get_data_freshness = AsyncMock(return_value=mock_stale_items)
            MockHS.return_value = mock_hs_instance
            mock_engine.pool = mock_pool

            svc = HealthAlertService(mock_session)
            await svc.check_and_alert()

        mock_telegram.send_message.assert_called()


class TestCooldown:
    """Test 4-hour cooldown between same alert type."""

    @pytest.fixture
    def mock_session(self):
        session = AsyncMock()
        session.execute = AsyncMock()
        return session

    @pytest.mark.asyncio
    async def test_cooldown_prevents_repeat_alert(self, mock_session):
        """Same alert type within 4h should not re-send."""
        from app.services.health_alert_service import (
            HealthAlertService, _last_alert_times, COOLDOWN_HOURS,
        )

        # Set cooldown as if alert was sent 1 hour ago
        _last_alert_times.clear()
        _last_alert_times["job_failures"] = datetime.now(timezone.utc) - timedelta(hours=1)

        # Mock: 3 failures present
        mock_fail_result = MagicMock()
        row = MagicMock()
        row.job_id = "daily_price_crawl_hose"
        row.fail_count = 3
        mock_fail_result.fetchall.return_value = [row]
        mock_session.execute = AsyncMock(return_value=mock_fail_result)

        mock_stale_items = []
        mock_pool = MagicMock()
        mock_pool.size.return_value = 5
        mock_pool.checkedout.return_value = 1

        mock_telegram = AsyncMock()
        mock_telegram.is_configured = True
        mock_telegram.send_message = AsyncMock()

        with patch("app.services.health_alert_service.HealthService") as MockHS, \
             patch("app.services.health_alert_service.engine") as mock_engine, \
             patch("app.services.health_alert_service.telegram_bot", mock_telegram):
            mock_hs_instance = AsyncMock()
            mock_hs_instance.get_data_freshness = AsyncMock(return_value=mock_stale_items)
            MockHS.return_value = mock_hs_instance
            mock_engine.pool = mock_pool

            svc = HealthAlertService(mock_session)
            await svc.check_and_alert()

        # Should NOT send because of cooldown
        mock_telegram.send_message.assert_not_called()

    @pytest.mark.asyncio
    async def test_cooldown_expires_after_4h(self, mock_session):
        """Alert re-sends after 4h cooldown expires."""
        from app.services.health_alert_service import (
            HealthAlertService, _last_alert_times, COOLDOWN_HOURS,
        )

        # Set cooldown as if alert was sent 5 hours ago (expired)
        _last_alert_times.clear()
        _last_alert_times["job_failures"] = datetime.now(timezone.utc) - timedelta(hours=5)

        mock_fail_result = MagicMock()
        row = MagicMock()
        row.job_id = "daily_price_crawl_hose"
        row.fail_count = 3
        mock_fail_result.fetchall.return_value = [row]
        mock_session.execute = AsyncMock(return_value=mock_fail_result)

        mock_stale_items = []
        mock_pool = MagicMock()
        mock_pool.size.return_value = 5
        mock_pool.checkedout.return_value = 1

        mock_telegram = AsyncMock()
        mock_telegram.is_configured = True
        mock_telegram.send_message = AsyncMock()

        with patch("app.services.health_alert_service.HealthService") as MockHS, \
             patch("app.services.health_alert_service.engine") as mock_engine, \
             patch("app.services.health_alert_service.telegram_bot", mock_telegram):
            mock_hs_instance = AsyncMock()
            mock_hs_instance.get_data_freshness = AsyncMock(return_value=mock_stale_items)
            MockHS.return_value = mock_hs_instance
            mock_engine.pool = mock_pool

            svc = HealthAlertService(mock_session)
            await svc.check_and_alert()

        # Should send because cooldown expired
        mock_telegram.send_message.assert_called()


class TestPoolExhaustion:
    """Test DB pool exhaustion detection."""

    @pytest.fixture
    def mock_session(self):
        session = AsyncMock()
        session.execute = AsyncMock()
        return session

    @pytest.mark.asyncio
    async def test_pool_exhaustion_triggers_alert(self, mock_session):
        """Alert fires when checked_out / size > 0.8."""
        from app.services.health_alert_service import HealthAlertService, _last_alert_times

        _last_alert_times.clear()

        # No failures
        mock_fail_result = MagicMock()
        mock_fail_result.fetchall.return_value = []
        mock_session.execute = AsyncMock(return_value=mock_fail_result)

        mock_stale_items = []

        # Pool: 5 out of 5 checked out = 100% > 80%
        mock_pool = MagicMock()
        mock_pool.size.return_value = 5
        mock_pool.checkedout.return_value = 5

        mock_telegram = AsyncMock()
        mock_telegram.is_configured = True
        mock_telegram.send_message = AsyncMock()

        with patch("app.services.health_alert_service.HealthService") as MockHS, \
             patch("app.services.health_alert_service.engine") as mock_engine, \
             patch("app.services.health_alert_service.telegram_bot", mock_telegram):
            mock_hs_instance = AsyncMock()
            mock_hs_instance.get_data_freshness = AsyncMock(return_value=mock_stale_items)
            MockHS.return_value = mock_hs_instance
            mock_engine.pool = mock_pool

            svc = HealthAlertService(mock_session)
            await svc.check_and_alert()

        mock_telegram.send_message.assert_called()


# ---- MessageFormatter.health_alert Tests ----

class TestHealthAlertFormat:
    """Test MessageFormatter.health_alert generates Vietnamese HTML."""

    def test_job_failures_alert_format(self):
        """health_alert for job_failures returns Vietnamese HTML."""
        from app.telegram.formatter import MessageFormatter

        msg = MessageFormatter.health_alert(
            "job_failures",
            ["Crawl giá HOSE (3 lần thất bại)"],
        )
        assert "🔴" in msg or "🟡" in msg
        assert "Crawl giá HOSE" in msg
        assert "Xem chi tiết" in msg
        assert "/dashboard/health" in msg
        # HTML tags
        assert "<b>" in msg

    def test_stale_data_alert_format(self):
        """health_alert for stale_data returns Vietnamese message."""
        from app.telegram.formatter import MessageFormatter

        msg = MessageFormatter.health_alert(
            "stale_data",
            ["Giá cổ phiếu (>96h)"],
        )
        assert "Giá cổ phiếu" in msg
        assert "<b>" in msg

    def test_pool_exhaustion_alert_format(self):
        """health_alert for pool_exhaustion returns alert message."""
        from app.telegram.formatter import MessageFormatter

        msg = MessageFormatter.health_alert(
            "pool_exhaustion",
            ["5/5 kết nối đang sử dụng (100%)"],
        )
        assert "100%" in msg
        assert "<b>" in msg


# ---- Scheduler Job Registration ----

class TestHealthAlertSchedulerJob:
    """Test health_alert_check job is registered."""

    def test_job_name_in_mapping(self):
        """health_alert_check should be in _JOB_NAMES."""
        from app.scheduler.manager import _JOB_NAMES

        assert "health_alert_check" in _JOB_NAMES

    def test_scheduler_registers_job(self):
        """configure_jobs should register health_alert_check."""
        with patch("app.scheduler.manager.scheduler") as mock_scheduler, \
             patch("app.scheduler.manager.settings") as mock_settings:
            mock_settings.timezone = "Asia/Ho_Chi_Minh"
            mock_scheduler.add_job = MagicMock()
            mock_scheduler.add_listener = MagicMock()

            from app.scheduler.manager import configure_jobs
            configure_jobs()

            # Check that health_alert_check was registered
            add_job_calls = mock_scheduler.add_job.call_args_list
            job_ids = [
                c.kwargs.get("id") or (c.args[1] if len(c.args) > 1 else None)
                for c in add_job_calls
            ]
            assert "health_alert_check" in job_ids
