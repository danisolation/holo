"""Tests for AI Accuracy Tracking Service (Phase 65)."""
import pytest
from datetime import date

from app.services.accuracy_tracking_service import compute_verdict, HOLD_THRESHOLD_PCT


class TestComputeVerdict:
    """Unit tests for verdict logic."""

    def test_mua_price_up_is_correct(self):
        assert compute_verdict("mua", 2.5) == "correct"

    def test_mua_price_down_is_incorrect(self):
        assert compute_verdict("mua", -1.0) == "incorrect"

    def test_ban_price_down_is_correct(self):
        assert compute_verdict("ban", -3.0) == "correct"

    def test_ban_price_up_is_incorrect(self):
        assert compute_verdict("ban", 1.5) == "incorrect"

    def test_giu_within_threshold_is_correct(self):
        assert compute_verdict("giu", 1.5) == "correct"
        assert compute_verdict("giu", -1.5) == "correct"
        assert compute_verdict("giu", 0.0) == "correct"

    def test_giu_outside_threshold_is_incorrect(self):
        assert compute_verdict("giu", 3.0) == "incorrect"
        assert compute_verdict("giu", -2.5) == "incorrect"

    def test_giu_at_boundary(self):
        assert compute_verdict("giu", HOLD_THRESHOLD_PCT) == "correct"
        assert compute_verdict("giu", -HOLD_THRESHOLD_PCT) == "correct"

    def test_mua_zero_change_is_incorrect(self):
        assert compute_verdict("mua", 0.0) == "incorrect"

    def test_ban_zero_change_is_incorrect(self):
        assert compute_verdict("ban", 0.0) == "incorrect"

    def test_unknown_direction_returns_pending(self):
        assert compute_verdict("unknown", 5.0) == "pending"

    def test_case_insensitive(self):
        assert compute_verdict("MUA", 2.0) == "correct"
        assert compute_verdict("BAN", -2.0) == "correct"
        assert compute_verdict("GIU", 0.5) == "correct"


class TestAIAccuracyModel:
    """Test the AIAccuracy model can be imported."""

    def test_model_importable(self):
        from app.models.ai_accuracy import AIAccuracy
        assert AIAccuracy.__tablename__ == "ai_accuracy"

    def test_model_in_init(self):
        from app.models import AIAccuracy
        assert AIAccuracy.__tablename__ == "ai_accuracy"


class TestAccuracyTrackingServiceImport:
    """Test service is importable."""

    def test_service_importable(self):
        from app.services.accuracy_tracking_service import AccuracyTrackingService
        assert AccuracyTrackingService is not None

    def test_api_endpoint_importable(self):
        from app.api.accuracy import router
        assert router is not None
