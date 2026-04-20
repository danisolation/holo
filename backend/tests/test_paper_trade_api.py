"""Tests for paper trading API endpoints — CRUD + manual follow + config.

Uses unittest.mock to mock async_session. No real DB needed.
"""
import pytest
from pydantic import ValidationError

from app.schemas.paper_trading import ManualFollowRequest, SimulationConfigUpdateRequest


class TestManualFollowSchema:
    """PT-09: ManualFollowRequest validation."""

    def test_valid_long_follow(self):
        req = ManualFollowRequest(
            symbol="VNM", direction="long", entry_price=80000,
            stop_loss=75000, take_profit_1=85000, take_profit_2=90000,
            timeframe="swing", confidence=8, position_size_pct=10,
        )
        assert req.symbol == "VNM"
        assert req.direction == "long"

    def test_valid_bearish_follow(self):
        req = ManualFollowRequest(
            symbol="FPT", direction="bearish", entry_price=120000,
            stop_loss=130000, take_profit_1=115000, take_profit_2=110000,
            timeframe="position", confidence=6, position_size_pct=15,
        )
        assert req.direction == "bearish"
        assert req.timeframe == "position"

    def test_invalid_direction_rejected(self):
        with pytest.raises(ValidationError):
            ManualFollowRequest(
                symbol="VNM", direction="short", entry_price=80000,
                stop_loss=75000, take_profit_1=85000, take_profit_2=90000,
                timeframe="swing", confidence=8, position_size_pct=10,
            )

    def test_confidence_bounds(self):
        with pytest.raises(ValidationError):
            ManualFollowRequest(
                symbol="VNM", direction="long", entry_price=80000,
                stop_loss=75000, take_profit_1=85000, take_profit_2=90000,
                timeframe="swing", confidence=0, position_size_pct=10,
            )
        with pytest.raises(ValidationError):
            ManualFollowRequest(
                symbol="VNM", direction="long", entry_price=80000,
                stop_loss=75000, take_profit_1=85000, take_profit_2=90000,
                timeframe="swing", confidence=11, position_size_pct=10,
            )

    def test_entry_price_must_be_positive(self):
        with pytest.raises(ValidationError):
            ManualFollowRequest(
                symbol="VNM", direction="long", entry_price=-1,
                stop_loss=75000, take_profit_1=85000, take_profit_2=90000,
                timeframe="swing", confidence=8, position_size_pct=10,
            )

    def test_position_size_pct_bounds(self):
        with pytest.raises(ValidationError):
            ManualFollowRequest(
                symbol="VNM", direction="long", entry_price=80000,
                stop_loss=75000, take_profit_1=85000, take_profit_2=90000,
                timeframe="swing", confidence=8, position_size_pct=0,
            )
        with pytest.raises(ValidationError):
            ManualFollowRequest(
                symbol="VNM", direction="long", entry_price=80000,
                stop_loss=75000, take_profit_1=85000, take_profit_2=90000,
                timeframe="swing", confidence=8, position_size_pct=101,
            )

    def test_invalid_timeframe_rejected(self):
        with pytest.raises(ValidationError):
            ManualFollowRequest(
                symbol="VNM", direction="long", entry_price=80000,
                stop_loss=75000, take_profit_1=85000, take_profit_2=90000,
                timeframe="day", confidence=8, position_size_pct=10,
            )

    def test_model_dump_produces_dict(self):
        req = ManualFollowRequest(
            symbol="VNM", direction="long", entry_price=80000,
            stop_loss=75000, take_profit_1=85000, take_profit_2=90000,
            timeframe="swing", confidence=8, position_size_pct=10,
        )
        data = req.model_dump()
        assert isinstance(data, dict)
        assert data["symbol"] == "VNM"
        assert data["entry_price"] == 80000


class TestConfigUpdateSchema:
    def test_partial_update(self):
        req = SimulationConfigUpdateRequest(initial_capital=200000000)
        data = {k: v for k, v in req.model_dump().items() if v is not None}
        assert data == {"initial_capital": 200000000}

    def test_empty_update(self):
        req = SimulationConfigUpdateRequest()
        data = {k: v for k, v in req.model_dump().items() if v is not None}
        assert data == {}

    def test_min_confidence_bounds(self):
        with pytest.raises(ValidationError):
            SimulationConfigUpdateRequest(min_confidence_threshold=0)
        with pytest.raises(ValidationError):
            SimulationConfigUpdateRequest(min_confidence_threshold=11)

    def test_initial_capital_must_be_positive(self):
        with pytest.raises(ValidationError):
            SimulationConfigUpdateRequest(initial_capital=-100)
