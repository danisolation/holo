---
phase: 22
slug: paper-trade-foundation
date: 2025-07-18
---

# Phase 22 Validation Strategy

## Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.4.2 + pytest-asyncio |
| Config file | `backend/pytest.ini` (asyncio_mode=auto) |
| Quick run command | `cd backend && python -m pytest tests/test_paper_trade_*.py tests/test_position_sizing.py -x -q` |
| Full suite command | `cd backend && python -m pytest tests/ -x -q` |

## Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| PT-02 | State machine: valid transitions succeed, invalid transitions raise error | unit | `pytest tests/test_paper_trade_state_machine.py -x` | ❌ Wave 0 |
| PT-02 | All 7 statuses exist in TradeStatus enum | unit | `pytest tests/test_paper_trade_model.py -x` | ❌ Wave 0 |
| PT-03 | apply_partial_tp closes 50%, moves SL to breakeven | unit | `pytest tests/test_paper_trade_pnl.py::test_apply_partial_tp -x` | ❌ Wave 0 |
| PT-03 | Half-quantity rounds to 100-lot boundary | unit | `pytest tests/test_paper_trade_pnl.py::test_partial_tp_lot_rounding -x` | ❌ Wave 0 |
| PT-05 | Position sizing rounds to 100-share lots | unit | `pytest tests/test_position_sizing.py -x` | ❌ Wave 0 |
| PT-05 | Position sizing returns 0 when capital insufficient | unit | `pytest tests/test_position_sizing.py::test_insufficient_capital -x` | ❌ Wave 0 |
| PT-05 | SimulationConfig has initial_capital, auto_track, min_confidence | unit | `pytest tests/test_paper_trade_model.py::test_simulation_config_fields -x` | ❌ Wave 0 |
| PT-07 | P&L calculation: LONG with no partial TP | unit | `pytest tests/test_paper_trade_pnl.py::test_long_full_exit -x` | ❌ Wave 0 |
| PT-07 | P&L calculation: LONG with partial TP (TP1 + TP2) | unit | `pytest tests/test_paper_trade_pnl.py::test_long_partial_tp_then_tp2 -x` | ❌ Wave 0 |
| PT-07 | P&L calculation: LONG with partial TP (TP1 + SL) | unit | `pytest tests/test_paper_trade_pnl.py::test_long_partial_tp_then_sl -x` | ❌ Wave 0 |
| PT-07 | P&L calculation: BEARISH direction inverted | unit | `pytest tests/test_paper_trade_pnl.py::test_bearish_pnl -x` | ❌ Wave 0 |
| PT-07 | P&L returns both VND and percentage | unit | `pytest tests/test_paper_trade_pnl.py::test_pnl_returns_vnd_and_pct -x` | ❌ Wave 0 |

## Sampling Rate
- **Per task commit:** `cd backend && python -m pytest tests/test_paper_trade_*.py tests/test_position_sizing.py -x -q`
- **Per wave merge:** `cd backend && python -m pytest tests/ -x -q`
- **Phase gate:** Full suite green before `/gsd-verify-work`

## Wave 0 Gaps
- [ ] `tests/test_paper_trade_model.py` — covers PT-02 enum, PT-05 SimulationConfig fields
- [ ] `tests/test_paper_trade_state_machine.py` — covers PT-02 transitions
- [ ] `tests/test_paper_trade_pnl.py` — covers PT-03 partial TP, PT-07 P&L calculation
- [ ] `tests/test_position_sizing.py` — covers PT-05 lot rounding
