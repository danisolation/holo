---
phase: 23
slug: position-monitoring-auto-track
type: infrastructure
generated: auto
---

# Phase 23 Context: Position Monitoring & Auto-Track

## Phase Goal
System automatically creates paper trades from valid signals and monitors positions daily for TP/SL/timeout hits.

## Requirements
- **PT-01**: Auto-track all valid AI signals (score > 0) as paper trades
- **PT-04**: Daily position monitoring — check SL/TP/timeout against OHLCV
- **PT-06**: PENDING trades activate at D+1 open price (no lookahead bias)
- **PT-08**: Exclude score=0 invalid signals with deduplication

## Research-Backed Constraints

### Scheduler Integration
- Hook into existing scheduler chain: `combined → trading_signal → signal_alerts`
- Add two new jobs after `signal_alerts`:
  1. `auto_track_signals` — creates paper trades from new valid signals
  2. `monitor_positions` — checks open positions against daily OHLCV
- Use APScheduler 3.11 (already installed), follow `backend/app/scheduler/manager.py` patterns
- Jobs run as async functions with injected DB session

### Auto-Track Logic
- Source: `ai_analyses` table where `analysis_type = 'trading_signal'`
- Filter: `score > 0` AND not already tracked (dedup by ai_analysis_id)
- Extract from `raw_response` JSONB: entry, SL, TP1, TP2, direction, timeframe, confidence, position_size_pct, risk_reward_ratio
- Create PaperTrade in PENDING status
- Position sizing: use `calculate_position_size()` from Phase 22 service
- SimulationConfig: read `min_confidence_threshold` and `auto_track_enabled` from singleton row

### Position Monitor Logic
- Run daily after market close (after price crawl completes)
- Load all ACTIVE and PARTIAL_TP paper trades
- For PENDING trades: check if D+1 open price available → activate at open price
- For each active position:
  - Fetch latest daily OHLCV for the ticker
  - Check SL: if low <= effective_stop_loss → close at SL price (CLOSED_SL)
  - Check TP1 (if ACTIVE): if high >= take_profit_1 → apply_partial_tp()
  - Check TP2 (if PARTIAL_TP): if high >= take_profit_2 → close at TP2 (CLOSED_TP2)
  - Ambiguous bar rule: if both SL and TP breached same day → SL wins (conservative)
  - Check timeout: swing > 15 trading days, position > 60 trading days → close at market close price

### Batch Query Strategy (Aiven pool constraint)
- Pool: pool_size=5, max_overflow=3 (8 max connections)
- Query 1: `SELECT * FROM paper_trades WHERE status IN ('pending', 'active', 'partial_tp')`
- Query 2: `SELECT * FROM daily_prices WHERE ticker_id IN (...) AND date = :today ORDER BY ticker_id`
- Process in memory — no N+1 queries
- Use existing `backend/app/db/session.py` async session pattern

### Fill Prices
- PENDING → ACTIVE: entry_date = D+1, entry at D+1 open price from daily_prices
- SL hit: exit at effective_stop_loss price (not actual low)
- TP1 hit: partial_exit_price = take_profit_1
- TP2 hit: exit_price = take_profit_2
- Timeout: exit at market close price (daily_prices.close)

### Edge Cases
- No OHLCV data for a ticker on a given day → skip that position (market holiday, suspended)
- Signal already tracked → skip (dedup by ai_analysis_id UNIQUE constraint or check)
- SimulationConfig auto_track_enabled = false → skip auto-track job
- No open positions → monitor job returns early
