"""Tests for corporate actions enhancements: CORP-06.

Tests cover:
- alert_sent boolean field on CorporateEvent model
- Migration 008 structure
- RIGHTS_ISSUE type in TYPE_MAP and RELEVANT_TYPES
- RIGHTS_ISSUE factor formula returns 1.0 (no price adjustment — rights are optional)
- Regression: existing factor formulas unchanged
"""
from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest


# --- Task 1: alert_sent column and migration ---


class TestAlertSentField:
    """Test CorporateEvent model has alert_sent boolean field."""

    def test_model_has_alert_sent_attribute(self):
        """CorporateEvent model class has alert_sent column."""
        from app.models.corporate_event import CorporateEvent

        # Column should exist on the model
        assert hasattr(CorporateEvent, "alert_sent"), (
            "CorporateEvent model missing alert_sent attribute"
        )

    def test_alert_sent_column_properties(self):
        """alert_sent is Boolean, nullable=False, server_default='false'."""
        from app.models.corporate_event import CorporateEvent

        col = CorporateEvent.__table__.columns["alert_sent"]
        assert str(col.type) == "BOOLEAN", f"Expected BOOLEAN, got {col.type}"
        assert col.nullable is False, "alert_sent should be NOT NULL"
        assert col.server_default is not None, "alert_sent should have server_default"
        # server_default.arg can be a text clause or string depending on SQLAlchemy version
        default_val = getattr(col.server_default.arg, "text", col.server_default.arg)
        assert default_val == "false", (
            f"Expected server_default='false', got '{default_val}'"
        )

    def test_event_type_comment_includes_rights_issue(self):
        """Model docstring or event_type comment mentions RIGHTS_ISSUE."""
        from app.models.corporate_event import CorporateEvent

        # The event_type column comment in the model should mention RIGHTS_ISSUE
        col = CorporateEvent.__table__.columns["event_type"]
        assert col.comment is None or "RIGHTS_ISSUE" in (col.comment or ""), (
            "This test validates the source code mentions RIGHTS_ISSUE"
        )
        # Also check model module docstring
        import app.models.corporate_event as mod
        assert "RIGHTS_ISSUE" in mod.__doc__, (
            "Module docstring should mention RIGHTS_ISSUE event type"
        )


# --- Task 2: RIGHTS_ISSUE type mapping and factor formula ---


class TestRightsIssueTypeMapping:
    """Test RIGHTS_ISSUE type in crawler TYPE_MAP and RELEVANT_TYPES."""

    def test_type_map_has_rights_issue(self):
        """TYPE_MAP maps VNDirect 'RIGHT' to internal 'RIGHTS_ISSUE'."""
        from app.crawlers.corporate_event_crawler import TYPE_MAP

        assert "RIGHT" in TYPE_MAP, "TYPE_MAP missing 'RIGHT' key"
        assert TYPE_MAP["RIGHT"] == "RIGHTS_ISSUE", (
            f"Expected TYPE_MAP['RIGHT'] == 'RIGHTS_ISSUE', got '{TYPE_MAP.get('RIGHT')}'"
        )

    def test_relevant_types_includes_right(self):
        """RELEVANT_TYPES string includes 'RIGHT' for API query."""
        from app.crawlers.corporate_event_crawler import RELEVANT_TYPES

        assert "RIGHT" in RELEVANT_TYPES, (
            f"RELEVANT_TYPES missing 'RIGHT': {RELEVANT_TYPES}"
        )

    def test_type_map_size(self):
        """TYPE_MAP has 4 entries (3 original + RIGHTS_ISSUE)."""
        from app.crawlers.corporate_event_crawler import TYPE_MAP

        assert len(TYPE_MAP) == 4, f"Expected 4 TYPE_MAP entries, got {len(TYPE_MAP)}"

    def test_existing_types_unchanged(self):
        """Original 3 type mappings still work (regression)."""
        from app.crawlers.corporate_event_crawler import TYPE_MAP

        assert TYPE_MAP["DIVIDEND"] == "CASH_DIVIDEND"
        assert TYPE_MAP["STOCKDIV"] == "STOCK_DIVIDEND"
        assert TYPE_MAP["KINDDIV"] == "BONUS_SHARES"


class TestRightsIssueFactor:
    """Test _compute_single_factor returns 1.0 for RIGHTS_ISSUE."""

    def _make_event(self, event_type, dividend_amount=None, ratio=None, ex_date=None):
        """Create a mock CorporateEvent."""
        from unittest.mock import MagicMock
        event = MagicMock()
        event.event_type = event_type
        event.dividend_amount = Decimal(str(dividend_amount)) if dividend_amount is not None else None
        event.ratio = Decimal(str(ratio)) if ratio is not None else None
        event.ex_date = ex_date or date(2025, 5, 14)
        event.event_source_id = "test_event"
        return event

    @pytest.mark.asyncio
    async def test_rights_issue_factor_is_one(self):
        """RIGHTS_ISSUE returns factor 1.0 — rights are optional, no price adjustment."""
        from app.services.corporate_action_service import CorporateActionService
        from unittest.mock import AsyncMock

        svc = CorporateActionService.__new__(CorporateActionService)
        svc.session = AsyncMock()

        event = self._make_event("RIGHTS_ISSUE", ratio=50)
        factor = await svc._compute_single_factor(event, ticker_id=1)
        assert factor == Decimal("1.0"), (
            f"RIGHTS_ISSUE factor should be 1.0, got {factor}"
        )

    @pytest.mark.asyncio
    async def test_rights_issue_factor_zero_ratio(self):
        """RIGHTS_ISSUE with zero ratio also returns 1.0."""
        from app.services.corporate_action_service import CorporateActionService
        from unittest.mock import AsyncMock

        svc = CorporateActionService.__new__(CorporateActionService)
        svc.session = AsyncMock()

        event = self._make_event("RIGHTS_ISSUE", ratio=0)
        factor = await svc._compute_single_factor(event, ticker_id=1)
        assert factor == Decimal("1.0")

    @pytest.mark.asyncio
    async def test_rights_issue_factor_no_ratio(self):
        """RIGHTS_ISSUE with None ratio returns 1.0."""
        from app.services.corporate_action_service import CorporateActionService
        from unittest.mock import AsyncMock

        svc = CorporateActionService.__new__(CorporateActionService)
        svc.session = AsyncMock()

        event = self._make_event("RIGHTS_ISSUE")
        factor = await svc._compute_single_factor(event, ticker_id=1)
        assert factor == Decimal("1.0")

    @pytest.mark.asyncio
    async def test_existing_cash_dividend_unchanged(self):
        """Regression: CASH_DIVIDEND factor formula still works."""
        from app.services.corporate_action_service import CorporateActionService
        from unittest.mock import AsyncMock

        svc = CorporateActionService.__new__(CorporateActionService)
        svc.session = AsyncMock()
        svc._get_close_before = AsyncMock(return_value=Decimal("84000"))

        event = self._make_event("CASH_DIVIDEND", dividend_amount=2000)
        factor = await svc._compute_single_factor(event, ticker_id=1)
        expected = (Decimal("84000") - Decimal("2000")) / Decimal("84000")
        assert factor == expected

    @pytest.mark.asyncio
    async def test_existing_stock_dividend_unchanged(self):
        """Regression: STOCK_DIVIDEND factor formula still works."""
        from app.services.corporate_action_service import CorporateActionService
        from unittest.mock import AsyncMock

        svc = CorporateActionService.__new__(CorporateActionService)
        svc.session = AsyncMock()

        event = self._make_event("STOCK_DIVIDEND", ratio=20)
        factor = await svc._compute_single_factor(event, ticker_id=1)
        expected = Decimal("100") / Decimal("120")
        assert factor == expected

    @pytest.mark.asyncio
    async def test_existing_bonus_shares_unchanged(self):
        """Regression: BONUS_SHARES factor formula still works."""
        from app.services.corporate_action_service import CorporateActionService
        from unittest.mock import AsyncMock

        svc = CorporateActionService.__new__(CorporateActionService)
        svc.session = AsyncMock()

        event = self._make_event("BONUS_SHARES", ratio=10)
        factor = await svc._compute_single_factor(event, ticker_id=1)
        expected = Decimal("100") / Decimal("110")
        assert factor == expected


class TestMigration008:
    """Test migration 008 exists and has correct structure."""

    def _load_migration(self):
        """Load migration module by file path (alembic/versions not a package)."""
        import importlib.util
        from pathlib import Path

        migration_path = Path(__file__).parent.parent / "alembic" / "versions" / "008_corporate_actions_enhancements.py"
        spec = importlib.util.spec_from_file_location("migration_008", migration_path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    def test_migration_file_importable(self):
        """Migration 008 can be imported."""
        mod = self._load_migration()
        assert mod is not None

    def test_migration_revision(self):
        """Migration has correct revision chain."""
        mod = self._load_migration()
        assert mod.revision == "008"
        assert mod.down_revision == "007"

    def test_migration_has_upgrade_downgrade(self):
        """Migration has upgrade and downgrade functions."""
        mod = self._load_migration()
        assert callable(getattr(mod, "upgrade", None))
        assert callable(getattr(mod, "downgrade", None))
