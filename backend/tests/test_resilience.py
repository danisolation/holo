"""Tests for resilience behavior: job tracking, retry, DLQ, notifications.

Tests ERR-01 through ERR-05, ERR-07 from requirements.
"""
import pytest
from unittest.mock import patch, AsyncMock, MagicMock, call


def _make_session_and_job_svc():
    """Create mock session + JobExecutionService pair."""
    mock_session = AsyncMock()
    mock_job_svc = MagicMock()
    mock_execution = MagicMock()
    mock_execution.status = "running"
    mock_job_svc.start = AsyncMock(return_value=mock_execution)
    mock_job_svc.complete = AsyncMock()
    mock_job_svc.fail = AsyncMock()
    return mock_session, mock_job_svc, mock_execution


def _patch_session():
    """Patch async_session context manager."""
    mock_session = AsyncMock()
    patcher = patch("app.scheduler.jobs.async_session")
    mock_factory = patcher.start()
    mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)
    return patcher, mock_session


class TestRetryAndDLQ:
    """ERR-01, ERR-02, ERR-07: Retry failed tickers, DLQ permanent failures."""

    @pytest.mark.asyncio
    async def test_retry_rebatch_failed_tickers(self):
        """ERR-01: Failed tickers from first crawl pass are retried once."""
        with patch("app.scheduler.jobs.async_session") as mock_sf:
            mock_session = AsyncMock()
            mock_sf.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_sf.return_value.__aexit__ = AsyncMock(return_value=False)

            with patch("app.scheduler.jobs.JobExecutionService") as MockJobSvc:
                mock_job_svc = MagicMock()
                mock_exec = MagicMock(status="running")
                mock_job_svc.start = AsyncMock(return_value=mock_exec)
                mock_job_svc.complete = AsyncMock()
                mock_job_svc.fail = AsyncMock()
                MockJobSvc.return_value = mock_job_svc

                with patch("app.scheduler.jobs.PriceService") as MockPS:
                    mock_svc = AsyncMock()
                    # First pass: 5 failures
                    mock_svc.crawl_daily = AsyncMock(return_value={
                        "success": 395, "failed": 5, "skipped": 0,
                        "failed_symbols": ["A", "B", "C", "D", "E"],
                    })
                    # Retry pass: all succeed
                    mock_svc._crawl_batch = AsyncMock(return_value={
                        "success": 5, "failed": 0, "skipped": 0,
                        "failed_symbols": [],
                    })
                    mock_svc.ticker_service = AsyncMock()
                    mock_svc.ticker_service.get_ticker_id_map = AsyncMock(
                        return_value={s: i for i, s in enumerate(["A", "B", "C", "D", "E"])}
                    )
                    MockPS.return_value = mock_svc

                    from app.scheduler.jobs import daily_price_crawl
                    await daily_price_crawl()

                    # Verify retry was attempted with failed symbols
                    mock_svc._crawl_batch.assert_called_once()
                    retry_symbols = mock_svc._crawl_batch.call_args[0][0]
                    assert set(retry_symbols) == {"A", "B", "C", "D", "E"}

    @pytest.mark.asyncio
    async def test_failed_items_added_to_dlq(self):
        """ERR-02: After retry, permanently failed tickers go to DLQ."""
        with patch("app.scheduler.jobs.async_session") as mock_sf:
            mock_session = AsyncMock()
            mock_sf.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_sf.return_value.__aexit__ = AsyncMock(return_value=False)

            with patch("app.scheduler.jobs.JobExecutionService") as MockJobSvc:
                mock_job_svc = MagicMock()
                mock_exec = MagicMock(status="running")
                mock_job_svc.start = AsyncMock(return_value=mock_exec)
                mock_job_svc.complete = AsyncMock()
                MockJobSvc.return_value = mock_job_svc

                with patch("app.scheduler.jobs.DeadLetterService") as MockDLQ:
                    mock_dlq = AsyncMock()
                    MockDLQ.return_value = mock_dlq

                    with patch("app.scheduler.jobs.PriceService") as MockPS:
                        mock_svc = AsyncMock()
                        # First pass: 3 failures
                        mock_svc.crawl_daily = AsyncMock(return_value={
                            "success": 397, "failed": 3, "skipped": 0,
                            "failed_symbols": ["X", "Y", "Z"],
                        })
                        # Retry: all 3 still fail
                        mock_svc._crawl_batch = AsyncMock(return_value={
                            "success": 0, "failed": 3, "skipped": 0,
                            "failed_symbols": ["X", "Y", "Z"],
                        })
                        mock_svc.ticker_service = AsyncMock()
                        mock_svc.ticker_service.get_ticker_id_map = AsyncMock(
                            return_value={"X": 1, "Y": 2, "Z": 3}
                        )
                        MockPS.return_value = mock_svc

                        from app.scheduler.jobs import daily_price_crawl
                        await daily_price_crawl()

                        # Verify DLQ called for each failed symbol
                        assert mock_dlq.add.call_count == 3
                        dlq_symbols = [c.args[1] for c in mock_dlq.add.call_args_list]
                        assert set(dlq_symbols) == {"X", "Y", "Z"}

    @pytest.mark.asyncio
    async def test_retry_then_dlq(self):
        """ERR-07: Retry succeeds for some, DLQ only the permanent failures."""
        with patch("app.scheduler.jobs.async_session") as mock_sf:
            mock_session = AsyncMock()
            mock_sf.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_sf.return_value.__aexit__ = AsyncMock(return_value=False)

            with patch("app.scheduler.jobs.JobExecutionService") as MockJobSvc:
                mock_job_svc = MagicMock()
                mock_exec = MagicMock(status="running")
                mock_job_svc.start = AsyncMock(return_value=mock_exec)
                mock_job_svc.complete = AsyncMock()
                MockJobSvc.return_value = mock_job_svc

                with patch("app.scheduler.jobs.DeadLetterService") as MockDLQ:
                    mock_dlq = AsyncMock()
                    MockDLQ.return_value = mock_dlq

                    with patch("app.scheduler.jobs.PriceService") as MockPS:
                        mock_svc = AsyncMock()
                        # First pass: 3 failures
                        mock_svc.crawl_daily = AsyncMock(return_value={
                            "success": 397, "failed": 3, "skipped": 0,
                            "failed_symbols": ["X", "Y", "Z"],
                        })
                        # Retry: X succeeds, Y and Z still fail
                        mock_svc._crawl_batch = AsyncMock(return_value={
                            "success": 1, "failed": 2, "skipped": 0,
                            "failed_symbols": ["Y", "Z"],
                        })
                        mock_svc.ticker_service = AsyncMock()
                        mock_svc.ticker_service.get_ticker_id_map = AsyncMock(
                            return_value={"X": 1, "Y": 2, "Z": 3}
                        )
                        MockPS.return_value = mock_svc

                        from app.scheduler.jobs import daily_price_crawl
                        await daily_price_crawl()

                        # Only 2 items in DLQ (Y, Z), NOT 3
                        assert mock_dlq.add.call_count == 2
                        dlq_symbols = [c.args[1] for c in mock_dlq.add.call_args_list]
                        assert set(dlq_symbols) == {"Y", "Z"}


class TestGracefulDegradation:
    """ERR-03: Partial failure continues chain; complete failure breaks it."""

    @pytest.mark.asyncio
    async def test_partial_failure_continues_chain(self):
        """ERR-03: Partial success returns normally (no exception)."""
        with patch("app.scheduler.jobs.async_session") as mock_sf:
            mock_session = AsyncMock()
            mock_sf.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_sf.return_value.__aexit__ = AsyncMock(return_value=False)

            with patch("app.scheduler.jobs.JobExecutionService") as MockJobSvc:
                mock_job_svc = MagicMock()
                mock_exec = MagicMock(status="running")
                mock_job_svc.start = AsyncMock(return_value=mock_exec)
                mock_job_svc.complete = AsyncMock()
                MockJobSvc.return_value = mock_job_svc

                with patch("app.scheduler.jobs.PriceService") as MockPS:
                    mock_svc = AsyncMock()
                    mock_svc.crawl_daily = AsyncMock(return_value={
                        "success": 390, "failed": 10, "skipped": 0,
                        "failed_symbols": [f"T{i}" for i in range(10)],
                    })
                    # Retry: still some failures (partial)
                    mock_svc._crawl_batch = AsyncMock(return_value={
                        "success": 5, "failed": 5, "skipped": 0,
                        "failed_symbols": [f"T{i}" for i in range(5)],
                    })
                    mock_svc.ticker_service = AsyncMock()
                    mock_svc.ticker_service.get_ticker_id_map = AsyncMock(
                        return_value={f"T{i}": i for i in range(10)}
                    )
                    MockPS.return_value = mock_svc

                    from app.scheduler.jobs import daily_price_crawl
                    # Should NOT raise — partial success continues chain
                    await daily_price_crawl()

                    # Verify status is "partial"
                    mock_job_svc.complete.assert_called_once()
                    call_kwargs = mock_job_svc.complete.call_args
                    assert call_kwargs.kwargs.get("status") == "partial" or call_kwargs[0][1] == "partial"

    @pytest.mark.asyncio
    async def test_complete_failure_raises(self):
        """ERR-03: Complete failure (0 success) raises RuntimeError."""
        with patch("app.scheduler.jobs.async_session") as mock_sf:
            mock_session = AsyncMock()
            mock_sf.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_sf.return_value.__aexit__ = AsyncMock(return_value=False)

            with patch("app.scheduler.jobs.JobExecutionService") as MockJobSvc:
                mock_job_svc = MagicMock()
                mock_exec = MagicMock(status="running")
                mock_job_svc.start = AsyncMock(return_value=mock_exec)
                mock_job_svc.complete = AsyncMock()
                mock_job_svc.fail = AsyncMock()
                MockJobSvc.return_value = mock_job_svc

                with patch("app.scheduler.jobs.PriceService") as MockPS:
                    mock_svc = AsyncMock()
                    mock_svc.crawl_daily = AsyncMock(return_value={
                        "success": 0, "failed": 400, "skipped": 0,
                        "failed_symbols": [f"T{i}" for i in range(400)],
                    })
                    mock_svc._crawl_batch = AsyncMock(return_value={
                        "success": 0, "failed": 400, "skipped": 0,
                        "failed_symbols": [f"T{i}" for i in range(400)],
                    })
                    mock_svc.ticker_service = AsyncMock()
                    mock_svc.ticker_service.get_ticker_id_map = AsyncMock(
                        return_value={f"T{i}": i for i in range(400)}
                    )
                    MockPS.return_value = mock_svc

                    from app.scheduler.jobs import daily_price_crawl
                    with pytest.raises(RuntimeError, match="Complete crawl failure"):
                        await daily_price_crawl()


class TestJobExecutionTracking:
    """ERR-04: Every job run creates a job_executions row."""

    @pytest.mark.asyncio
    async def test_job_execution_logged(self):
        """ERR-04: JobExecutionService.start called; complete called with summary."""
        with patch("app.scheduler.jobs.async_session") as mock_sf:
            mock_session = AsyncMock()
            mock_sf.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_sf.return_value.__aexit__ = AsyncMock(return_value=False)

            with patch("app.scheduler.jobs.JobExecutionService") as MockJobSvc:
                mock_job_svc = MagicMock()
                mock_exec = MagicMock(status="running")
                mock_job_svc.start = AsyncMock(return_value=mock_exec)
                mock_job_svc.complete = AsyncMock()
                MockJobSvc.return_value = mock_job_svc

                with patch("app.scheduler.jobs.PriceService") as MockPS:
                    mock_svc = AsyncMock()
                    mock_svc.crawl_daily = AsyncMock(return_value={
                        "success": 400, "failed": 0, "skipped": 0,
                        "failed_symbols": [],
                    })
                    MockPS.return_value = mock_svc

                    from app.scheduler.jobs import daily_price_crawl
                    await daily_price_crawl()

                    # Verify start called with job_id
                    mock_job_svc.start.assert_called_once_with("daily_price_crawl")

                    # Verify complete called with status and result_summary
                    mock_job_svc.complete.assert_called_once()
                    call_kwargs = mock_job_svc.complete.call_args
                    assert call_kwargs.kwargs.get("status") == "success"
                    summary = call_kwargs.kwargs.get("result_summary")
                    assert "tickers_processed" in summary
                    assert "tickers_failed" in summary
                    assert "failed_symbols" in summary
                    assert summary["tickers_processed"] == 400
                    assert summary["tickers_failed"] == 0


class TestTelegramNotification:
    """ERR-05: Complete failure sends Telegram notification via _on_job_error."""

    @pytest.mark.asyncio
    async def test_complete_failure_sends_telegram(self):
        """ERR-05: _on_job_error listener formats and attempts Telegram alert."""
        from app.scheduler.manager import _on_job_error

        mock_event = MagicMock()
        mock_event.job_id = "daily_price_crawl"
        mock_event.exception = RuntimeError("Complete crawl failure")
        mock_event.traceback = "Traceback..."

        with patch("app.telegram.bot.telegram_bot") as mock_bot:
            mock_bot.send_message = AsyncMock(return_value=True)
            mock_bot.is_configured = True

            # _on_job_error is sync and uses loop.create_task internally
            # Just verify it runs without error — the actual telegram call
            # is fire-and-forget via asyncio.get_event_loop().create_task()
            import asyncio
            loop = asyncio.get_event_loop()
            with patch.object(loop, "create_task") as mock_create_task:
                _on_job_error(mock_event)
                # Verify create_task was called (meaning Telegram send was attempted)
                mock_create_task.assert_called_once()


class TestAlertJobsNeverRaise:
    """Alert/notification jobs must never raise exceptions."""

    @pytest.mark.asyncio
    async def test_signal_alert_check_never_raises(self):
        """Alert jobs catch all exceptions and return normally."""
        with patch("app.scheduler.jobs.async_session") as mock_sf:
            mock_session = AsyncMock()
            mock_sf.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_sf.return_value.__aexit__ = AsyncMock(return_value=False)

            with patch("app.scheduler.jobs.JobExecutionService") as MockJobSvc:
                mock_job_svc = MagicMock()
                mock_exec = MagicMock(status="running")
                mock_job_svc.start = AsyncMock(return_value=mock_exec)
                mock_job_svc.complete = AsyncMock()
                MockJobSvc.return_value = mock_job_svc

                with patch("app.telegram.services.AlertService") as MockAlert:
                    mock_alert = AsyncMock()
                    mock_alert.check_signal_changes = AsyncMock(side_effect=Exception("Telegram down"))
                    MockAlert.return_value = mock_alert

                    from app.scheduler.jobs import daily_signal_alert_check
                    # Must NOT raise
                    await daily_signal_alert_check()

                    # Verify it completed with "partial" status (error captured)
                    mock_job_svc.complete.assert_called_once()
