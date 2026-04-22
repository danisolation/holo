"""Tests for corporate actions: CORP-02, CORP-04.

Tests cover:
- CORP-02: Crawler type mapping and deduplication
- CORP-04: Job function exists and is callable

Note: CORP-01, CORP-03, CORP-05 removed — CorporateActionService deleted in v7.0.
"""
import asyncio
from datetime import date

import pytest


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
