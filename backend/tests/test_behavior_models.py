"""Unit tests for behavior tracking ORM models and Pydantic schemas.

Verifies model column definitions and schema validation.
Pure structure tests — no database needed.
"""
import pytest
from sqlalchemy import inspect


# ── Model Column Tests ───────────────────────────────────────────────────────


class TestBehaviorEventModel:
    """Verify BehaviorEvent ORM model structure."""

    def test_tablename(self):
        from app.models.behavior_event import BehaviorEvent
        assert BehaviorEvent.__tablename__ == "behavior_events"

    def test_columns_exist(self):
        from app.models.behavior_event import BehaviorEvent
        mapper = inspect(BehaviorEvent)
        col_names = {c.key for c in mapper.columns}
        assert {"id", "event_type", "ticker_id", "event_metadata", "created_at"} <= col_names

    def test_id_is_primary_key(self):
        from app.models.behavior_event import BehaviorEvent
        mapper = inspect(BehaviorEvent)
        pk_cols = [c.name for c in mapper.columns if c.primary_key]
        assert "id" in pk_cols


class TestHabitDetectionModel:
    """Verify HabitDetection ORM model structure."""

    def test_tablename(self):
        from app.models.habit_detection import HabitDetection
        assert HabitDetection.__tablename__ == "habit_detections"

    def test_columns_exist(self):
        from app.models.habit_detection import HabitDetection
        mapper = inspect(HabitDetection)
        col_names = {c.key for c in mapper.columns}
        assert {"id", "habit_type", "ticker_id", "trade_id", "evidence", "detected_at"} <= col_names


class TestRiskSuggestionModel:
    """Verify RiskSuggestion ORM model structure."""

    def test_tablename(self):
        from app.models.risk_suggestion import RiskSuggestion
        assert RiskSuggestion.__tablename__ == "risk_suggestions"

    def test_columns_exist(self):
        from app.models.risk_suggestion import RiskSuggestion
        mapper = inspect(RiskSuggestion)
        col_names = {c.key for c in mapper.columns}
        assert {"id", "current_level", "suggested_level", "reason", "status", "created_at", "responded_at"} <= col_names


class TestSectorPreferenceModel:
    """Verify SectorPreference ORM model structure."""

    def test_tablename(self):
        from app.models.sector_preference import SectorPreference
        assert SectorPreference.__tablename__ == "sector_preferences"

    def test_columns_exist(self):
        from app.models.sector_preference import SectorPreference
        mapper = inspect(SectorPreference)
        col_names = {c.key for c in mapper.columns}
        assert {"id", "sector", "total_trades", "win_count", "loss_count", "net_pnl", "preference_score", "updated_at"} <= col_names


# ── Schema Validation Tests ──────────────────────────────────────────────────


class TestBehaviorSchemas:
    """Verify Pydantic schemas validate correctly."""

    def test_behavior_event_create_valid(self):
        from app.schemas.behavior import BehaviorEventCreate
        evt = BehaviorEventCreate(event_type="ticker_view", ticker_symbol="VNM")
        assert evt.event_type == "ticker_view"
        assert evt.ticker_symbol == "VNM"

    def test_behavior_event_create_invalid_type(self):
        from app.schemas.behavior import BehaviorEventCreate
        with pytest.raises(Exception):
            BehaviorEventCreate(event_type="invalid_type")

    def test_behavior_event_create_pick_click(self):
        from app.schemas.behavior import BehaviorEventCreate
        evt = BehaviorEventCreate(event_type="pick_click", metadata={"pick_id": 1})
        assert evt.event_type == "pick_click"
        assert evt.metadata == {"pick_id": 1}

    def test_viewing_stats_response(self):
        from app.schemas.behavior import ViewingStatsResponse, ViewingStatItem
        item = ViewingStatItem(ticker_symbol="VNM", sector="Thực phẩm", view_count=15, last_viewed="2026-04-20")
        resp = ViewingStatsResponse(items=[item], total_views=15)
        assert resp.total_views == 15
        assert len(resp.items) == 1

    def test_habit_detections_response(self):
        from app.schemas.behavior import HabitDetectionsResponse, HabitDetectionItem
        item = HabitDetectionItem(habit_type="premature_sell", count=3, latest_ticker="VNM", latest_date="2026-04-20")
        resp = HabitDetectionsResponse(habits=[item], analysis_date="2026-04-20")
        assert len(resp.habits) == 1

    def test_sector_preferences_response(self):
        from app.schemas.behavior import SectorPreferencesResponse, SectorPreferenceItem
        item = SectorPreferenceItem(
            sector="Ngân hàng", total_trades=10, win_count=7, loss_count=3,
            net_pnl=5000000.0, win_rate=70.0, preference_score=0.62
        )
        resp = SectorPreferencesResponse(sectors=[item], insufficient_count=2)
        assert resp.insufficient_count == 2

    def test_risk_suggestion_response(self):
        from app.schemas.behavior import RiskSuggestionResponse
        resp = RiskSuggestionResponse(
            id=1, current_level=3, suggested_level=2,
            reason="3 lần lỗ liên tiếp", status="pending", created_at="2026-04-20T10:00:00"
        )
        assert resp.suggested_level == 2

    def test_risk_suggestion_respond_valid(self):
        from app.schemas.behavior import RiskSuggestionRespondRequest
        req = RiskSuggestionRespondRequest(action="accept")
        assert req.action == "accept"

    def test_risk_suggestion_respond_invalid(self):
        from app.schemas.behavior import RiskSuggestionRespondRequest
        with pytest.raises(Exception):
            RiskSuggestionRespondRequest(action="maybe")


# ── Model Registration Tests ─────────────────────────────────────────────────


class TestModelRegistration:
    """Verify all 4 new models are registered in __init__.py."""

    def test_behavior_event_in_init(self):
        from app.models import BehaviorEvent
        assert BehaviorEvent.__tablename__ == "behavior_events"

    def test_habit_detection_in_init(self):
        from app.models import HabitDetection
        assert HabitDetection.__tablename__ == "habit_detections"

    def test_risk_suggestion_in_init(self):
        from app.models import RiskSuggestion
        assert RiskSuggestion.__tablename__ == "risk_suggestions"

    def test_sector_preference_in_init(self):
        from app.models import SectorPreference
        assert SectorPreference.__tablename__ == "sector_preferences"
