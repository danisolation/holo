# Phase 22: Paper Trade Foundation - Context

**Gathered:** 2026-04-20
**Status:** Ready for planning
**Mode:** Auto-generated (infrastructure phase — discuss skipped)

<domain>
## Phase Boundary

Paper trade data model with correct state machine and P&L calculation exists and is verified by unit tests. Creates PaperTrade model, SimulationConfig model, Alembic migration, and core business logic for trade lifecycle and P&L computation.

</domain>

<decisions>
## Implementation Decisions

### Agent's Discretion
All implementation choices are at the agent's discretion — pure infrastructure phase. Use ROADMAP phase goal, success criteria, and codebase conventions to guide decisions.

Key constraints from research:
- State machine: PENDING → ACTIVE → PARTIAL_TP → CLOSED (sub-states: CLOSED_TP2, CLOSED_SL, CLOSED_TIMEOUT, CLOSED_MANUAL)
- Partial TP: 50% at TP1, move SL to entry (breakeven), remaining 50% targets TP2
- Entry at D+1 open price (prevent lookahead bias)
- SL wins on ambiguous bars (conservative fill when both SL and TP breach same day)
- Position sizing rounds to 100-share lots per VN exchange rules
- Exclude score=0 (invalid) signals from auto-tracking
- P&L in both VND absolute and % of entry
- Use Numeric(12,2) for prices following existing Trade model pattern
- Use Mapped[] + mapped_column() following existing SQLAlchemy 2.0 patterns
- Separate table from real trades (paper_trades, NOT reusing trades table)
- SimulationConfig: initial_capital, auto_track_enabled, min_confidence_threshold

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `backend/app/models/trade.py` — Trade model pattern (Mapped[], Numeric(12,2), ForeignKey to tickers)
- `backend/app/models/ai_analysis.py` — AIAnalysis with AnalysisType enum, JSONB raw_response
- `backend/app/models/__init__.py` — Base declarative base
- `backend/alembic/versions/012_trading_signal_type.py` — Latest migration pattern

### Established Patterns
- SQLAlchemy 2.0 Mapped[] annotations with mapped_column()
- Numeric(12,2) for VND prices, Integer for quantities
- BigInteger autoincrement primary keys
- ForeignKey to tickers.id for symbol reference
- TIMESTAMP(timezone=True) with server_default=func.now() for timestamps
- Python enum.Enum for status/type columns
- JSONB for flexible nested data (raw_response pattern)

### Integration Points
- Links to `tickers.id` via ForeignKey
- Links to `ai_analyses.id` for signal reference (which signal created this paper trade)
- Will be consumed by Phase 23 scheduler jobs and Phase 24 API endpoints

</code_context>

<specifics>
## Specific Ideas

No specific requirements — infrastructure phase. Refer to ROADMAP phase description and success criteria.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>
