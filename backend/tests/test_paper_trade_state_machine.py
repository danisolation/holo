"""Tests for paper trade state machine transitions.

Pure unit tests — no DB, no async. PT-02 coverage.
"""
import pytest
from app.models.paper_trade import TradeStatus
from app.services.paper_trade_service import VALID_TRANSITIONS, validate_transition


class TestValidTransitions:
    """PT-02: Valid state transitions succeed."""

    @pytest.mark.parametrize("current,target", [
        (TradeStatus.PENDING, TradeStatus.ACTIVE),
        (TradeStatus.PENDING, TradeStatus.CLOSED_MANUAL),
        (TradeStatus.ACTIVE, TradeStatus.PARTIAL_TP),
        (TradeStatus.ACTIVE, TradeStatus.CLOSED_SL),
        (TradeStatus.ACTIVE, TradeStatus.CLOSED_TIMEOUT),
        (TradeStatus.ACTIVE, TradeStatus.CLOSED_MANUAL),
        (TradeStatus.PARTIAL_TP, TradeStatus.CLOSED_TP2),
        (TradeStatus.PARTIAL_TP, TradeStatus.CLOSED_SL),
        (TradeStatus.PARTIAL_TP, TradeStatus.CLOSED_TIMEOUT),
        (TradeStatus.PARTIAL_TP, TradeStatus.CLOSED_MANUAL),
    ])
    def test_valid_transitions(self, current, target):
        assert validate_transition(current, target) is True

    @pytest.mark.parametrize("current,target", [
        (TradeStatus.PENDING, TradeStatus.CLOSED_TP2),
        (TradeStatus.PENDING, TradeStatus.PARTIAL_TP),
        (TradeStatus.PENDING, TradeStatus.CLOSED_SL),
        (TradeStatus.ACTIVE, TradeStatus.PENDING),
        (TradeStatus.PARTIAL_TP, TradeStatus.ACTIVE),
        (TradeStatus.PARTIAL_TP, TradeStatus.PENDING),
        (TradeStatus.CLOSED_SL, TradeStatus.ACTIVE),
        (TradeStatus.CLOSED_TP2, TradeStatus.ACTIVE),
        (TradeStatus.CLOSED_TIMEOUT, TradeStatus.ACTIVE),
        (TradeStatus.CLOSED_MANUAL, TradeStatus.ACTIVE),
    ])
    def test_invalid_transitions(self, current, target):
        assert validate_transition(current, target) is False


class TestTransitionMap:
    def test_closed_states_are_terminal(self):
        """All CLOSED_* states have no valid outgoing transitions."""
        terminal = [TradeStatus.CLOSED_TP2, TradeStatus.CLOSED_SL,
                    TradeStatus.CLOSED_TIMEOUT, TradeStatus.CLOSED_MANUAL]
        for state in terminal:
            assert VALID_TRANSITIONS[state] == set(), f"{state} should be terminal"

    def test_all_states_in_transition_map(self):
        """Every TradeStatus value appears as a key in VALID_TRANSITIONS."""
        for status in TradeStatus:
            assert status in VALID_TRANSITIONS, f"{status} missing from transition map"
