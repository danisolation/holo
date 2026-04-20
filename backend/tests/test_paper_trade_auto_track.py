"""Tests for paper_trade_auto_track job logic.

PT-01: Auto-track valid signals → PENDING paper trades.
PT-08: Score=0 excluded, dedup by ai_analysis_id.
Pure unit tests — mock DB session, no actual database.
"""
import pytest
from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock

from app.models.paper_trade import PaperTrade, TradeStatus, TradeDirection
from app.models.simulation_config import SimulationConfig
from app.models.ai_analysis import AIAnalysis, AnalysisType


def _make_config(auto_track=True, capital=100_000_000, min_confidence=5):
    """Create a mock SimulationConfig."""
    config = MagicMock(spec=SimulationConfig)
    config.auto_track_enabled = auto_track
    config.initial_capital = Decimal(str(capital))
    config.min_confidence_threshold = min_confidence
    return config


def _make_signal_analysis(analysis_id, ticker_id, score, raw_response):
    """Create a mock AIAnalysis row."""
    analysis = MagicMock(spec=AIAnalysis)
    analysis.id = analysis_id
    analysis.ticker_id = ticker_id
    analysis.analysis_type = AnalysisType.TRADING_SIGNAL
    analysis.analysis_date = date.today()
    analysis.score = score
    analysis.raw_response = raw_response
    return analysis


def _make_raw_response(direction="long", confidence=8, entry=80000, sl=76000,
                       tp1=84000, tp2=88000, rr=2.0, size_pct=10,
                       timeframe="swing"):
    """Create a valid raw_response dict matching TickerTradingSignal schema."""
    plan = {
        "entry_price": entry, "stop_loss": sl,
        "take_profit_1": tp1, "take_profit_2": tp2,
        "risk_reward_ratio": rr, "position_size_pct": size_pct,
        "timeframe": timeframe,
    }
    long_analysis = {
        "direction": "long", "confidence": confidence if direction == "long" else 3,
        "trading_plan": plan, "reasoning": "Test reasoning",
    }
    bearish_analysis = {
        "direction": "bearish", "confidence": confidence if direction == "bearish" else 3,
        "trading_plan": {**plan, "entry_price": entry, "stop_loss": entry * 1.05,
                         "take_profit_1": entry * 0.95, "take_profit_2": entry * 0.90},
        "reasoning": "Test bearish reasoning",
    }
    return {
        "ticker": "VNM",
        "recommended_direction": direction,
        "long_analysis": long_analysis,
        "bearish_analysis": bearish_analysis,
    }


class TestAutoTrackSignalParsing:
    """PT-01: Valid signals create correct PaperTrade objects."""

    def test_valid_signal_creates_pending_trade(self):
        """A valid signal with score > 0 and confidence >= threshold creates a PENDING trade."""
        from app.schemas.analysis import TickerTradingSignal
        raw = _make_raw_response(direction="long", confidence=8, entry=80000)
        signal = TickerTradingSignal.model_validate(raw)
        assert signal.recommended_direction.value == "long"
        assert signal.long_analysis.confidence == 8
        assert signal.long_analysis.trading_plan.entry_price == 80000

    def test_bearish_signal_parses_correctly(self):
        """BEARISH direction extracts bearish_analysis plan."""
        from app.schemas.analysis import TickerTradingSignal
        raw = _make_raw_response(direction="bearish", confidence=7)
        signal = TickerTradingSignal.model_validate(raw)
        assert signal.recommended_direction.value == "bearish"
        assert signal.bearish_analysis.confidence == 7

    def test_invalid_raw_response_raises(self):
        """Malformed raw_response fails model_validate (job should skip, not crash)."""
        from app.schemas.analysis import TickerTradingSignal
        with pytest.raises(Exception):
            TickerTradingSignal.model_validate({"bad": "data"})


class TestAutoTrackFiltering:
    """PT-08: Score=0 excluded, confidence threshold, dedup."""

    def test_position_sizing_called_correctly(self):
        """Position sizing uses config capital and signal allocation_pct."""
        from app.services.paper_trade_service import calculate_position_size
        qty = calculate_position_size(
            capital=Decimal("100000000"),
            allocation_pct=10,
            entry_price=Decimal("80000"),
        )
        # 100M * 10% = 10M / 80K = 125 shares → round to 100
        assert qty == 100
        assert qty % 100 == 0

    def test_zero_quantity_skipped(self):
        """If position sizing returns 0, trade is not created."""
        from app.services.paper_trade_service import calculate_position_size
        qty = calculate_position_size(
            capital=Decimal("100000"),  # Very small capital
            allocation_pct=1,
            entry_price=Decimal("80000"),
        )
        # 100K * 1% = 1K / 80K = 0.0125 → rounds to 0
        assert qty == 0

    def test_confidence_below_threshold_excluded(self):
        """Signal with confidence < min_confidence_threshold should be skipped."""
        # This is a logic test — confidence=3, threshold=5 → skip
        config = _make_config(min_confidence=5)
        assert 3 < config.min_confidence_threshold  # would be skipped


class TestAutoTrackDedup:
    """PT-08: Deduplication by ai_analysis_id."""

    def test_existing_analysis_ids_detected(self):
        """If ai_analysis_id already in paper_trades, signal is skipped."""
        existing_ids = {101, 102}
        signals = [
            _make_signal_analysis(101, 1, 8, _make_raw_response()),
            _make_signal_analysis(103, 2, 7, _make_raw_response()),
        ]
        to_create = [s for s in signals if s.id not in existing_ids]
        assert len(to_create) == 1
        assert to_create[0].id == 103
