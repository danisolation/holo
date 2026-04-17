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
        assert col.server_default.arg.text == "false", (
            f"Expected server_default='false', got '{col.server_default.arg.text}'"
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


class TestMigration008:
    """Test migration 008 exists and has correct structure."""

    def _load_migration(self):
        """Load migration module (can't use normal import — starts with digit)."""
        import importlib
        return importlib.import_module("alembic.versions.008_corporate_actions_enhancements")

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
