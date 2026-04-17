"""Tests for corporate actions: CORP-01 through CORP-05.

Tests cover:
- CORP-01: PriceResponse includes adjusted_close
- CORP-02: Crawler type mapping and deduplication
- CORP-03: Backward cumulative adjustment algorithm
- CORP-04: Job function exists and is callable
- CORP-05: Factor formulas for each event type (VN market)
"""
import asyncio
from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest


# --- CORP-05: Factor Formula Tests ---


class TestFactorFormulas:
    """Test adjustment factor computation for each event type.

    Formulas per 07-RESEARCH.md:
    - CASH_DIVIDEND: (close_before - dividend) / close_before
    - STOCK_DIVIDEND: 100 / (100 + ratio)
    - BONUS_SHARES: 100 / (100 + ratio)
    """

    def _make_event(self, event_type, dividend_amount=None, ratio=None, ex_date=None):
        """Create a mock CorporateEvent."""
        event = MagicMock()
        event.event_type = event_type
        event.dividend_amount = Decimal(str(dividend_amount)) if dividend_amount is not None else None
        event.ratio = Decimal(str(ratio)) if ratio is not None else None
        event.ex_date = ex_date or date(2025, 5, 14)
        event.event_source_id = "test_event"
        return event

    @pytest.mark.asyncio
    async def test_factor_cash_dividend(self):
        """VNM 2025: DIVIDEND 2000 VND, close ~84000 → factor ≈ 0.9762"""
        from app.services.corporate_action_service import CorporateActionService

        svc = CorporateActionService.__new__(CorporateActionService)
        svc.session = AsyncMock()
        svc._get_close_before = AsyncMock(return_value=Decimal("84000"))

        event = self._make_event("CASH_DIVIDEND", dividend_amount=2000)
        factor = await svc._compute_single_factor(event, ticker_id=1)
        expected = (Decimal("84000") - Decimal("2000")) / Decimal("84000")
        assert factor == expected
        assert Decimal("0.97") < factor < Decimal("0.98")

    @pytest.mark.asyncio
    async def test_factor_stock_dividend(self):
        """HPG 2025: STOCKDIV ratio=20 → factor = 100/120 ≈ 0.8333"""
        from app.services.corporate_action_service import CorporateActionService

        svc = CorporateActionService.__new__(CorporateActionService)
        svc.session = AsyncMock()

        event = self._make_event("STOCK_DIVIDEND", ratio=20)
        factor = await svc._compute_single_factor(event, ticker_id=1)
        expected = Decimal("100") / Decimal("120")
        assert factor == expected
        # Verify NOT using wrong formula: 1/(1+20) = 0.0476
        assert factor > Decimal("0.5"), (
            f"Factor {factor} suggests wrong formula (1/(1+ratio) instead of 100/(100+ratio))"
        )

    @pytest.mark.asyncio
    async def test_factor_bonus_shares(self):
        """HPG 2024: KINDDIV ratio=10 → factor = 100/110 ≈ 0.9091"""
        from app.services.corporate_action_service import CorporateActionService

        svc = CorporateActionService.__new__(CorporateActionService)
        svc.session = AsyncMock()

        event = self._make_event("BONUS_SHARES", ratio=10)
        factor = await svc._compute_single_factor(event, ticker_id=1)
        expected = Decimal("100") / Decimal("110")
        assert factor == expected
        assert Decimal("0.90") < factor < Decimal("0.92")

    @pytest.mark.asyncio
    async def test_factor_stock_dividend_large_ratio(self):
        """HPG 2022: STOCKDIV ratio=30 → factor = 100/130 ≈ 0.7692"""
        from app.services.corporate_action_service import CorporateActionService

        svc = CorporateActionService.__new__(CorporateActionService)
        svc.session = AsyncMock()

        event = self._make_event("STOCK_DIVIDEND", ratio=30)
        factor = await svc._compute_single_factor(event, ticker_id=1)
        expected = Decimal("100") / Decimal("130")
        assert factor == expected

    @pytest.mark.asyncio
    async def test_factor_zero_dividend(self):
        """Zero dividend → factor = 1.0 (no adjustment)."""
        from app.services.corporate_action_service import CorporateActionService

        svc = CorporateActionService.__new__(CorporateActionService)
        svc.session = AsyncMock()

        event = self._make_event("CASH_DIVIDEND", dividend_amount=0)
        factor = await svc._compute_single_factor(event, ticker_id=1)
        assert factor == Decimal("1.0")

    @pytest.mark.asyncio
    async def test_factor_missing_close_before(self):
        """No close_before available → factor = 1.0."""
        from app.services.corporate_action_service import CorporateActionService

        svc = CorporateActionService.__new__(CorporateActionService)
        svc.session = AsyncMock()
        svc._get_close_before = AsyncMock(return_value=None)

        event = self._make_event("CASH_DIVIDEND", dividend_amount=2000)
        factor = await svc._compute_single_factor(event, ticker_id=1)
        assert factor == Decimal("1.0")

    @pytest.mark.asyncio
    async def test_factor_zero_ratio(self):
        """Zero ratio → factor = 1.0."""
        from app.services.corporate_action_service import CorporateActionService

        svc = CorporateActionService.__new__(CorporateActionService)
        svc.session = AsyncMock()

        event = self._make_event("STOCK_DIVIDEND", ratio=0)
        factor = await svc._compute_single_factor(event, ticker_id=1)
        assert factor == Decimal("1.0")

    @pytest.mark.asyncio
    async def test_factor_unknown_type(self):
        """Unknown event type → factor = 1.0."""
        from app.services.corporate_action_service import CorporateActionService

        svc = CorporateActionService.__new__(CorporateActionService)
        svc.session = AsyncMock()

        event = self._make_event("UNKNOWN_TYPE")
        factor = await svc._compute_single_factor(event, ticker_id=1)
        assert factor == Decimal("1.0")


# --- CORP-03: Backward Cumulative Adjustment Tests ---


class TestBackwardAdjustment:
    """Test the backward cumulative adjustment algorithm."""

    def test_single_event(self):
        """One event: prices before ex_date adjusted, after unchanged."""
        from app.services.corporate_action_service import CorporateActionService

        svc = CorporateActionService.__new__(CorporateActionService)

        prices = [
            (1, date(2024, 6, 20), Decimal("50000")),
            (2, date(2024, 6, 14), Decimal("60000")),
            (3, date(2024, 6, 10), Decimal("55000")),
        ]
        factors = [(date(2024, 6, 15), Decimal("0.8"))]

        result = svc._compute_adjusted_prices(prices, factors)

        assert result[0] == (1, Decimal("50000.00"))
        assert result[1] == (2, Decimal("48000.00"))
        assert result[2] == (3, Decimal("44000.00"))

    def test_multiple_events(self):
        """Two events: cumulative product for oldest prices."""
        from app.services.corporate_action_service import CorporateActionService

        svc = CorporateActionService.__new__(CorporateActionService)

        prices = [
            (1, date(2024, 8, 1), Decimal("100000")),
            (2, date(2024, 6, 20), Decimal("100000")),
            (3, date(2024, 5, 1), Decimal("100000")),
        ]
        factors = [
            (date(2024, 7, 1), Decimal("0.9")),
            (date(2024, 6, 1), Decimal("0.8")),
        ]

        result = svc._compute_adjusted_prices(prices, factors)

        assert result[0] == (1, Decimal("100000.00"))
        assert result[1] == (2, Decimal("90000.00"))
        assert result[2] == (3, Decimal("72000.00"))

    def test_no_events(self):
        """No events: adjusted = raw close."""
        from app.services.corporate_action_service import CorporateActionService

        svc = CorporateActionService.__new__(CorporateActionService)

        prices = [
            (1, date(2024, 6, 20), Decimal("50000")),
            (2, date(2024, 6, 19), Decimal("49000")),
        ]
        factors = []

        result = svc._compute_adjusted_prices(prices, factors)
        assert result[0] == (1, Decimal("50000.00"))
        assert result[1] == (2, Decimal("49000.00"))

    def test_events_on_same_date(self):
        """Multiple events on same ex_date (e.g., HPG DIVIDEND + STOCKDIV on 2022-06-17)."""
        from app.services.corporate_action_service import CorporateActionService

        svc = CorporateActionService.__new__(CorporateActionService)

        prices = [
            (1, date(2024, 6, 20), Decimal("100000")),
            (2, date(2024, 6, 10), Decimal("100000")),
        ]
        factors = [
            (date(2024, 6, 15), Decimal("0.9")),
            (date(2024, 6, 15), Decimal("0.8")),
        ]

        result = svc._compute_adjusted_prices(prices, factors)
        assert result[0] == (1, Decimal("100000.00"))
        assert result[1] == (2, Decimal("72000.00"))  # 0.9 * 0.8 = 0.72


# --- CORP-02: Crawler Tests ---


class TestCrawlerTypeMapping:
    """Test VNDirect API type mapping and data extraction."""

    def test_type_mapping(self):
        """VNDirect types map to our internal enum."""
        from app.crawlers.corporate_event_crawler import TYPE_MAP

        assert TYPE_MAP["DIVIDEND"] == "CASH_DIVIDEND"
        assert TYPE_MAP["STOCKDIV"] == "STOCK_DIVIDEND"
        assert TYPE_MAP["KINDDIV"] == "BONUS_SHARES"
        assert len(TYPE_MAP) == 4  # CASH_DIVIDEND, STOCK_DIVIDEND, BONUS_SHARES, RIGHTS_ISSUE

    def test_parse_date_valid(self):
        """Valid date string parses correctly."""
        from app.crawlers.corporate_event_crawler import CorporateEventCrawler

        assert CorporateEventCrawler._parse_date("2025-05-14") == date(2025, 5, 14)

    def test_parse_date_none(self):
        """None date returns None."""
        from app.crawlers.corporate_event_crawler import CorporateEventCrawler

        assert CorporateEventCrawler._parse_date(None) is None

    def test_parse_date_invalid(self):
        """Invalid date returns None."""
        from app.crawlers.corporate_event_crawler import CorporateEventCrawler

        assert CorporateEventCrawler._parse_date("not-a-date") is None

    def test_vndirect_url(self):
        """VNDirect events API URL is correct."""
        from app.crawlers.corporate_event_crawler import VNDIRECT_EVENTS_URL

        assert VNDIRECT_EVENTS_URL == "https://api-finfo.vndirect.com.vn/v4/events"


# --- CORP-01: PriceResponse Tests ---


class TestPriceResponse:
    """Test that API returns adjusted_close."""

    def test_price_response_includes_adjusted_close(self):
        """PriceResponse model has adjusted_close field (CORP-01)."""
        from app.api.tickers import PriceResponse

        pr = PriceResponse(
            date="2024-01-01",
            open=100.0, high=110.0, low=90.0, close=105.0,
            volume=1000000,
            adjusted_close=102.5,
        )
        assert pr.adjusted_close == 102.5

    def test_price_response_adjusted_close_nullable(self):
        """adjusted_close defaults to None when not provided."""
        from app.api.tickers import PriceResponse

        pr = PriceResponse(
            date="2024-01-01",
            open=100.0, high=110.0, low=90.0, close=105.0,
            volume=1000000,
        )
        assert pr.adjusted_close is None


# --- CORP-04: Job Function Tests ---


class TestJobFunction:
    """Test daily_corporate_action_check job integration."""

    def test_job_function_exists(self):
        """daily_corporate_action_check is importable and async."""
        from app.scheduler.jobs import daily_corporate_action_check

        assert asyncio.iscoroutinefunction(daily_corporate_action_check)

    def test_manager_chains_corporate_action(self):
        """Manager _JOB_NAMES includes corporate action check."""
        from app.scheduler.manager import _JOB_NAMES

        assert "daily_corporate_action_check_triggered" in _JOB_NAMES
