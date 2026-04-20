# Phase 19: AI Trading Signal Pipeline - Research

**Researched:** 2026-04-20
**Domain:** Gemini AI structured output, Pydantic nested schemas, PostgreSQL ENUM migration, batch analysis pipeline
**Confidence:** HIGH

## Summary

Phase 19 adds a 5th analysis type (`trading_signal`) to the existing Gemini AI pipeline. The codebase already has a well-established pattern for batched AI analysis (4 existing types: technical, fundamental, sentiment, combined) with circuit breaker protection, 429/503 retry logic, and dead-letter queue integration. The new type follows this exact pattern but with larger output per ticker (~300 tokens vs ~50 tokens), requiring reduced batch size (15 vs 25) and increased token budgets (max_output_tokens: 32768, thinking_budget: 2048).

The primary complexity is in the 3-level nested Pydantic schema (`TradingSignalBatchResponse → TickerTradingSignal → DirectionAnalysis → TradingPlanDetail`) which has been verified to work with `google-genai 1.73.1`'s `response_schema` parameter. A critical pitfall was identified: the existing `ai_analyses.score` column has a `CHECK (score BETWEEN 1 AND 10)` constraint, but CONTEXT.md specifies storing `score=0` for invalid signals — migration 012 must also alter this constraint.

The trading signal pipeline requires per-ticker context from Phase 17 indicators (ATR, ADX, Stochastic) and Phase 18 S/R levels (pivot points, Fibonacci), plus current price and 52-week high/low from daily_prices. This context feeds into the prompt to ground Gemini's price targets, with post-validation enforcing entry ±5% of current price, SL within 3×ATR, and TP within 5×ATR.

**Primary recommendation:** Follow the exact existing pattern for run_X_analysis/batch_analyzer/prompt_builder/context_getter, extending `_call_gemini_with_retry` to accept configurable `max_output_tokens` and `thinking_budget` parameters rather than hardcoding them.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- VN Market Framing: Direction enum LONG/BEARISH (not SHORT). System instruction explicitly states BEARISH = bearish outlook, NOT literal short-selling
- Schema: 3-level nested Pydantic — TradingSignalBatchResponse → TickerTradingSignal → DirectionAnalysis → TradingPlanDetail
- TradingPlanDetail fields: entry_price, stop_loss, take_profit_1, take_profit_2, risk_reward_ratio (ge=0.5), position_size_pct (1-100), timeframe (SWING/POSITION enum)
- Batch size: 15 tickers (reduced from 25)
- Batch delay: 4.0s (same as existing)
- Migration 012: ALTER TYPE analysis_type ADD VALUE 'trading_signal'
- No new table — reuse ai_analyses with raw_response JSONB storing full signal
- signal field: recommended_direction.value ("long" or "bearish")
- score field: recommended_direction's confidence (1-10)
- reasoning field: recommended_direction's reasoning
- Post-validation: entry ±5% current, SL within 3×ATR, TP within 5×ATR, R:R recalculated
- Invalid signals: store with signal="invalid", score=0, reasoning="Validation failed: {reason}"
- Config: trading_signal_batch_size=15, trading_signal_thinking_budget=2048, trading_signal_max_tokens=32768
- Temperature: 0.2
- Pipeline: 5th step after combined analysis in analyze_all_tickers()
- API: Extend GET /api/analysis/{symbol}/latest (no new endpoint)

### Agent's Discretion
- Exact system instruction wording (follow Vietnamese guidance)
- Prompt formatting/structure details
- Logging verbosity for trading signal pipeline
- Whether to run trading signals for all tickers or only those with recent price data

### Deferred Ideas (OUT OF SCOPE)
- Telegram alert formatting for trading signals — Phase 19 only adds backend pipeline
- Dashboard display of trading signals — handled in Phase 20
- Chart overlay of entry/SL/TP lines — handled in Phase 21
- Multi-model consensus (Gemini + Claude for signal verification) — future consideration
- Backtesting validation of generated signals — out of v3.0 scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| PLAN-01 | User can view dual-direction analysis (LONG outlook + BEARISH outlook) with confidence per direction | Schema: TickerTradingSignal with long_analysis + bearish_analysis, each having confidence 1-10. Stored in raw_response JSONB. Direction enum verified working with google-genai. |
| PLAN-02 | User can view specific entry price, stop-loss, and take-profit targets for the recommended direction | TradingPlanDetail schema with entry_price, stop_loss, take_profit_1, take_profit_2. Post-validation ensures grounded targets. Prompt includes S/R + Fibonacci levels from Phase 18. |
| PLAN-03 | User can view risk/reward ratio for each trading plan | TradingPlanDetail.risk_reward_ratio (ge=0.5). Post-validation recalculates R:R from actual entry/SL/TP and compares to Gemini's value. |
| PLAN-04 | User can view recommended timeframe (swing/position) for each trading plan | Timeframe enum with SWING (3-15 days) and POSITION (weeks+). No intraday/scalp per VN T+2.5 constraint. |
| PLAN-05 | User can view position sizing suggestion (% of portfolio) for each trading plan | TradingPlanDetail.position_size_pct (1-100 integer). Prompt instructs Gemini to consider volatility (ATR) and confidence. |
| PLAN-06 | User can read Vietnamese explanation of the trading rationale for each direction | DirectionAnalysis.reasoning (Vietnamese, max 300 chars). System instruction in Vietnamese. |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| google-genai | 1.73.1 | Gemini API structured output with nested Pydantic | Already in use, verified nested schema support [VERIFIED: local python import] |
| pydantic | 2.x (via fastapi) | Response schema definition + post-validation | Already the schema layer; Gemini accepts Pydantic BaseModel directly [VERIFIED: codebase] |
| sqlalchemy | 2.0.49+ | Async PostgreSQL operations, upsert | Already in use for all DB operations [VERIFIED: requirements.txt] |
| alembic | 1.18.x | Database migration for ENUM extension | Established migration pattern (001-011 exist) [VERIFIED: codebase] |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| tenacity | 9.1.x | Retry on ServerError | Already wraps _call_gemini_with_retry [VERIFIED: codebase] |
| loguru | 0.7.x | Structured logging | Already used throughout service [VERIFIED: codebase] |
| apscheduler | 3.11.x | Job chaining for daily pipeline | Already manages job chain in scheduler/manager.py [VERIFIED: codebase] |

**No new dependencies needed.** All libraries are already installed and in use.

## Architecture Patterns

### Existing 4-Type Analysis Pattern (FOLLOW EXACTLY)

The codebase has a consistent pattern for each analysis type. The trading signal type must follow it precisely:

```
For each analysis type:
1. run_{type}_analysis()          — public method, gathers context, calls _run_batched_analysis
2. _analyze_{type}_batch()        — builds prompt, calls Gemini, handles fallback parsing
3. _build_{type}_prompt()         — formats ticker data into prompt string
4. _get_{type}_context()          — queries DB for per-ticker input data
5. {Type}BatchResponse schema     — Pydantic model for Gemini response_schema
6. {TYPE}_SYSTEM_INSTRUCTION      — module-level system instruction string
7. {TYPE}_FEW_SHOT               — module-level few-shot example
8. ANALYSIS_TEMPERATURES[type]    — per-type temperature config
```

### New Files/Changes Required

```
backend/
├── alembic/versions/
│   └── 012_trading_signal_type.py          # NEW: migration
├── app/
│   ├── schemas/
│   │   └── analysis.py                     # MODIFY: add 5 new Pydantic classes + update SummaryResponse
│   ├── models/
│   │   └── ai_analysis.py                  # MODIFY: add TRADING_SIGNAL to AnalysisType enum
│   ├── services/
│   │   └── ai_analysis_service.py          # MODIFY: add trading signal methods + update analyze_all_tickers
│   ├── config.py                           # MODIFY: add 3 new settings
│   ├── api/
│   │   └── analysis.py                     # MODIFY: add trading_signal endpoint + update summary
│   └── scheduler/
│       ├── jobs.py                         # MODIFY: add daily_trading_signal_analysis job
│       └── manager.py                      # MODIFY: add chain link + job name mapping
```

### Pattern: Trading Signal Context Gathering

```python
# Source: Existing _get_technical_context pattern in ai_analysis_service.py
# VERIFIED from codebase lines 790-875

async def _get_trading_signal_context(self, ticker_id: int, symbol: str) -> dict | None:
    """Get comprehensive context for trading signal generation.
    
    Combines: latest indicators (ATR, ADX, RSI, Stochastic, BBands),
    S/R levels (pivot, support, resistance, fibonacci),
    current price, and 52-week high/low.
    """
    # 1. Latest indicators from TechnicalIndicator (includes Phase 17+18 columns)
    # 2. Latest close price from DailyPrice  
    # 3. 52-week high/low from DailyPrice (SELECT MAX(high), MIN(low) WHERE date > today - 365)
    # Returns None if no indicator data (skip ticker)
```

### Pattern: Post-Validation

```python
# DESIGNED PER CONTEXT.MD — Agent's discretion on implementation detail

def _validate_trading_signal(
    signal: TickerTradingSignal, 
    current_price: float, 
    atr: float
) -> tuple[bool, str]:
    """Validate a single ticker's trading signal.
    
    Returns (is_valid, reason).
    Checks both long_analysis and bearish_analysis plans.
    """
    for analysis in [signal.long_analysis, signal.bearish_analysis]:
        plan = analysis.trading_plan
        # Entry within ±5% of current_price
        if abs(plan.entry_price - current_price) / current_price > 0.05:
            return False, f"Entry {plan.entry_price} outside ±5% of current {current_price}"
        # SL within 3×ATR of entry
        if abs(plan.stop_loss - plan.entry_price) > 3 * atr:
            return False, f"SL {plan.stop_loss} exceeds 3×ATR ({3*atr:.0f}) from entry"
        # TP within 5×ATR of entry  
        for tp in [plan.take_profit_1, plan.take_profit_2]:
            if abs(tp - plan.entry_price) > 5 * atr:
                return False, f"TP {tp} exceeds 5×ATR ({5*atr:.0f}) from entry"
    return True, ""
```

### Pattern: _call_gemini_with_retry Extension

```python
# Current signature (hardcoded max_output_tokens=16384, thinking_budget=1024):
async def _call_gemini_with_retry(self, prompt, response_schema, temperature=0.2, system_instruction=None):

# MUST EXTEND to accept overrides for trading signals:
async def _call_gemini_with_retry(
    self, prompt, response_schema, temperature=0.2, 
    system_instruction=None,
    max_output_tokens: int = 16384,      # NEW param, default preserves existing behavior
    thinking_budget: int | None = None,   # NEW param, None = use model default (1024 for 2.5)
):
```

### Anti-Patterns to Avoid
- **Don't create a separate Gemini call method for trading signals.** Extend `_call_gemini_with_retry` with optional params. The existing 4 types pass defaults.
- **Don't bypass _run_batched_analysis.** The 429/503 retry, rate limiting, and commit-per-batch logic must be reused.
- **Don't store trading signal data in a new table.** CONTEXT.md explicitly says reuse ai_analyses with raw_response JSONB.
- **Don't hardcode batch_size=15 in the method.** Use `settings.trading_signal_batch_size` via config, and the `_run_batched_analysis` already reads `self.batch_size`. Trading signal method should temporarily override `self.batch_size` or pass it as a parameter.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Batch orchestration | Custom loop with sleep/retry | `_run_batched_analysis()` | Already handles 429/503, rate limiting, commit-per-batch, circuit breaker [VERIFIED: codebase] |
| Gemini structured output | Manual JSON parsing | `response_schema=PydanticModel` + `response.parsed` | google-genai validates against schema automatically [VERIFIED: local test] |
| Job chaining | Custom scheduler logic | APScheduler `_on_job_executed` listener | Existing chain: combined → signal_alerts. Insert trading_signal between them [VERIFIED: codebase] |
| DB upsert | ORM merge + flush | `_store_analysis()` raw SQL INSERT ON CONFLICT | Avoids SQLAlchemy Enum serialization issues with asyncpg [VERIFIED: codebase] |

**Key insight:** 90% of this phase is wiring — the infrastructure (batching, retry, circuit breaker, storage, scheduling) is already built. The novel work is schema design, prompt engineering, and post-validation.

## Common Pitfalls

### Pitfall 1: Score CHECK Constraint Blocks score=0 (CRITICAL)
**What goes wrong:** CONTEXT.md says invalid signals should be stored with `score=0`. The existing `ai_analyses` table has `CHECK (score BETWEEN 1 AND 10)`. Inserting score=0 violates the constraint → `IntegrityError`.
**Why it happens:** The CHECK was defined in migration 002 for the original analysis types where 1-10 was always valid.
**How to avoid:** Migration 012 must also `ALTER TABLE ai_analyses DROP CONSTRAINT ...` and recreate with `CHECK (score BETWEEN 0 AND 10)`. Alternatively, store invalid signals with `score=1` and use `signal="invalid"` as the indicator. The ALTER approach is cleaner.
**Warning signs:** Test with an invalid signal — if it throws IntegrityError, the constraint wasn't updated.
**Verified:** `CHECK (score BETWEEN 1 AND 10)` confirmed in migration 002 line 58 [VERIFIED: codebase]

### Pitfall 2: Batch Size Override Leaking to Other Analysis Types
**What goes wrong:** If `run_trading_signal_analysis()` modifies `self.batch_size` before calling `_run_batched_analysis()`, other concurrent analysis types may inherit the smaller batch size.
**Why it happens:** `self.batch_size` is shared instance state, and the `_gemini_lock` serializes calls, but if batch_size is set before acquiring the lock (in `analyze_all_tickers`), it leaks.
**How to avoid:** Either pass batch_size as a parameter to `_run_batched_analysis()` (preferred), or save/restore `self.batch_size` around the call. The cleanest approach: add `batch_size_override: int | None = None` parameter to `_run_batched_analysis()`.
**Warning signs:** Technical/fundamental batches suddenly processing only 15 tickers instead of 25.

### Pitfall 3: _call_gemini_with_retry Signature Change Breaks Existing Callers
**What goes wrong:** Adding `max_output_tokens` and `thinking_budget` as new parameters changes the method signature. If `_call_gemini` passes these via positional args in `gemini_breaker.call()`, the order could mismatch.
**Why it happens:** `gemini_breaker.call(self._call_gemini_with_retry, prompt, response_schema, temperature, system_instruction)` — these are passed positionally.
**How to avoid:** Add new parameters as keyword-only (after `*`), or ensure they're at the end with defaults. The existing callers don't pass them, so defaults apply. But verify `gemini_breaker.call()` passes kwargs correctly.
**Warning signs:** Existing analysis types start failing after the method signature change.

### Pitfall 4: Gemini Structured Output Nesting Depth Limitation
**What goes wrong:** 3-level nesting (BatchResponse → TickerSignal → DirectionAnalysis → TradingPlanDetail) may cause Gemini to produce malformed JSON or truncated output.
**Why it happens:** Deeper nesting = more tokens required. With 15 tickers × 2 directions × 7 plan fields + reasoning, output could exceed token budget.
**How to avoid:** max_output_tokens=32768 is sufficient (15 tickers × ~300 tokens = ~4500 tokens). The fallback parse chain (retry at 0.05 temp → manual JSON parse) already exists for all types.
**Warning signs:** `response.parsed is None` frequently for trading signals. Monitor via existing log warnings.
**Verified:** Nested Pydantic schema generates valid JSON schema and is accepted by google-genai [VERIFIED: local python test]

### Pitfall 5: 52-Week High/Low Query Performance
**What goes wrong:** Querying `MAX(high), MIN(low) FROM daily_prices WHERE date > today - 365` for each of 800 tickers is 800 queries with full table scans on a partitioned table.
**Why it happens:** daily_prices is partitioned by year. A 365-day window spans 2 partitions.
**How to avoid:** Batch the 52-week query: single query with `GROUP BY ticker_id` for all tickers at once, before the per-ticker loop. Or skip 52-week data if it's not essential (it's prompt context, not a hard requirement).
**Warning signs:** Context gathering phase takes > 60 seconds (existing types take < 5s).

### Pitfall 6: Job Chain Insertion Point
**What goes wrong:** Trading signal analysis must run AFTER combined analysis completes (it needs all prior analyses as context). If inserted at the wrong chain point, it runs with stale data.
**Why it happens:** The existing chain is: `combined → signal_alert_check + hnx_upcom_analysis`. Trading signals should be inserted between combined and signal_alerts.
**How to avoid:** In `_on_job_executed`: when `daily_combined_triggered` completes → trigger `daily_trading_signal_analysis`. When `daily_trading_signal_triggered` completes → trigger `daily_signal_alert_check + hnx_upcom_analysis` (existing behavior).
**Warning signs:** Trading signals don't have access to latest indicator/S/R data if chain order is wrong.

### Pitfall 7: ALTER TYPE in Transaction
**What goes wrong:** PostgreSQL's `ALTER TYPE ... ADD VALUE` cannot run inside a transaction block. Alembic normally runs migrations inside transactions.
**Why it happens:** PostgreSQL limitation on ENUM type modification.
**How to avoid:** Use `op.execute("COMMIT")` before `ALTER TYPE` or use `autocommit=True` on the operation. The existing migration 003 uses `ALTER TYPE analysis_type ADD VALUE IF NOT EXISTS 'combined'` and it worked — but verify that Alembic's transaction handling hasn't changed.
**Warning signs:** Migration 012 fails with "ALTER TYPE ... ADD VALUE cannot be executed inside a transaction block".
**Verified:** Migration 003 successfully used this pattern [VERIFIED: codebase]

## Code Examples

### Schema Definition (Pydantic)
```python
# Source: Verified pattern from existing schemas + CONTEXT.md decisions
# backend/app/schemas/analysis.py — NEW classes

from enum import Enum
from pydantic import BaseModel, Field

class Direction(str, Enum):
    """Trading signal direction."""
    LONG = "long"
    BEARISH = "bearish"

class Timeframe(str, Enum):
    """Trading timeframe — NO intraday/scalp (T+2.5)."""
    SWING = "swing"        # 3-15 days
    POSITION = "position"  # weeks+

class TradingPlanDetail(BaseModel):
    """Concrete entry/SL/TP targets for one direction."""
    entry_price: float
    stop_loss: float
    take_profit_1: float
    take_profit_2: float
    risk_reward_ratio: float = Field(ge=0.5)
    position_size_pct: int = Field(ge=1, le=100)
    timeframe: Timeframe

class DirectionAnalysis(BaseModel):
    """Analysis for one direction (LONG or BEARISH)."""
    direction: Direction
    confidence: int = Field(ge=1, le=10)
    trading_plan: TradingPlanDetail
    reasoning: str = Field(description="Vietnamese explanation, max 300 chars")

class TickerTradingSignal(BaseModel):
    """Dual-direction trading signal for one ticker."""
    ticker: str
    recommended_direction: Direction
    long_analysis: DirectionAnalysis
    bearish_analysis: DirectionAnalysis

class TradingSignalBatchResponse(BaseModel):
    """Batch response for trading signal analysis."""
    signals: list[TickerTradingSignal]
```

### Migration 012 Pattern
```python
# Source: Existing migration 003 pattern [VERIFIED: codebase]
# backend/alembic/versions/012_trading_signal_type.py

def upgrade() -> None:
    # Add 'trading_signal' to existing analysis_type ENUM
    op.execute("ALTER TYPE analysis_type ADD VALUE IF NOT EXISTS 'trading_signal';")
    
    # CRITICAL: Allow score=0 for invalid trading signals
    # Current constraint: CHECK (score BETWEEN 1 AND 10)
    op.execute("ALTER TABLE ai_analyses DROP CONSTRAINT IF EXISTS ai_analyses_score_check;")
    op.execute("ALTER TABLE ai_analyses ADD CONSTRAINT ai_analyses_score_check CHECK (score BETWEEN 0 AND 10);")

def downgrade() -> None:
    # Cannot remove ENUM value in PostgreSQL
    # Restore original constraint
    op.execute("ALTER TABLE ai_analyses DROP CONSTRAINT IF EXISTS ai_analyses_score_check;")
    op.execute("ALTER TABLE ai_analyses ADD CONSTRAINT ai_analyses_score_check CHECK (score BETWEEN 1 AND 10);")
```

### _run_batched_analysis with Batch Size Override
```python
# Source: Existing _run_batched_analysis pattern [VERIFIED: codebase lines 460-607]

async def _run_batched_analysis(
    self,
    ticker_data: dict[str, dict],
    ticker_ids: dict[str, int],
    analysis_type: AnalysisType,
    batch_analyzer,
    batch_size_override: int | None = None,  # NEW: for trading_signal's 15-ticker batches
) -> dict:
    symbols = list(ticker_data.keys())
    batch_size = batch_size_override or self.batch_size  # Use override if provided
    # ... rest of existing logic with batch_size instead of self.batch_size
```

### analyze_all_tickers Extension
```python
# Source: Existing analyze_all_tickers [VERIFIED: codebase lines 177-212]

async def analyze_all_tickers(self, analysis_type: str = "both", ticker_filter=None) -> dict:
    # ... existing lock acquisition ...
    
    # NEW: Add trading_signal to "all" type
    if analysis_type in ("trading_signal", "all"):
        results["trading_signal"] = await self.run_trading_signal_analysis(ticker_filter=ticker_filter)
    
    return results
```

### Scheduler Chain Update
```python
# Source: Existing _on_job_executed chain in manager.py [VERIFIED: codebase lines 158-175]

# BEFORE (existing):
# daily_combined_triggered → daily_signal_alert_check + daily_hnx_upcom_analysis

# AFTER (with trading signal inserted):
# daily_combined_triggered → daily_trading_signal_analysis
# daily_trading_signal_triggered → daily_signal_alert_check + daily_hnx_upcom_analysis
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| max_output_tokens=16384 for all types | Per-type token budgets (32768 for trading signals) | This phase | Prevents truncation of deeply nested output |
| thinking_budget=1024 for all types | Per-type thinking budgets (2048 for trading signals) | This phase | Better reasoning for dual-direction analysis |
| score BETWEEN 1 AND 10 | score BETWEEN 0 AND 10 | This phase | Allows score=0 for validation-failed signals |
| 4 analysis types | 5 analysis types (+ trading_signal) | This phase | Extends pipeline without new infrastructure |

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | PostgreSQL CHECK constraint name is `ai_analyses_score_check` (auto-generated) | Pitfall 1 | Migration fails; would need to query pg_constraint to find actual name |
| A2 | 15 tickers × ~300 tokens/ticker = ~4500 tokens fits within 32768 max_output_tokens | Pitfall 4 | Output truncation; would need further batch size reduction |
| A3 | `ALTER TYPE ... ADD VALUE` in migration 012 will work the same as 003 (no transaction issues) | Pitfall 7 | Migration failure; would need COMMIT workaround |
| A4 | Gemini 2.5-flash-lite handles 3-level nested structured output reliably | Architecture | Frequent parse failures; would need schema simplification |

## Open Questions

1. **CHECK Constraint Name**
   - What we know: Migration 002 defines `CHECK (score BETWEEN 1 AND 10)` inline
   - What's unclear: PostgreSQL auto-generates constraint name — it could be `ai_analyses_score_check` or a hash-based name
   - Recommendation: Use `DROP CONSTRAINT IF EXISTS` with both possible names, or query `information_schema.constraint_column_usage` in migration to find actual name. Safest: use `ALTER TABLE ai_analyses DROP CONSTRAINT` with the correct name found via `SELECT conname FROM pg_constraint WHERE conrelid = 'ai_analyses'::regclass AND contype = 'c';`

2. **52-Week High/Low Efficiency**
   - What we know: daily_prices is partitioned by year; per-ticker 365-day scan is expensive
   - What's unclear: Whether 52w data is essential for prompt quality vs. nice-to-have
   - Recommendation: Include 52w high/low in prompt but batch-query all tickers at once (`GROUP BY ticker_id`). If too slow, make it optional and log performance metrics.

3. **On-Demand Single Ticker Trading Signals**
   - What we know: `analyze_single_ticker()` runs all 4 types; should it also run trading signals?
   - What's unclear: CONTEXT.md doesn't explicitly address on-demand trading signals
   - Recommendation: Include trading signals in `analyze_single_ticker()` for consistency. The 5th type adds minimal overhead (1 API call for 1 ticker).

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.x + pytest-asyncio 0.24.x |
| Config file | backend/pytest.ini or pyproject.toml |
| Quick run command | `cd backend && python -m pytest tests/ -x -q --tb=short` |
| Full suite command | `cd backend && python -m pytest tests/ -v` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| PLAN-01 | Dual-direction analysis with confidence | unit | `pytest tests/test_trading_signal_schemas.py::test_direction_enum -x` | ❌ Wave 0 |
| PLAN-02 | Entry/SL/TP targets in trading plan | unit | `pytest tests/test_trading_signal_schemas.py::test_trading_plan_detail -x` | ❌ Wave 0 |
| PLAN-03 | R:R ratio calculation + validation | unit | `pytest tests/test_trading_signal_validation.py::test_rr_ratio -x` | ❌ Wave 0 |
| PLAN-04 | Timeframe enum (swing/position) | unit | `pytest tests/test_trading_signal_schemas.py::test_timeframe_enum -x` | ❌ Wave 0 |
| PLAN-05 | Position sizing 1-100% | unit | `pytest tests/test_trading_signal_schemas.py::test_position_size_bounds -x` | ❌ Wave 0 |
| PLAN-06 | Vietnamese reasoning field | unit | `pytest tests/test_trading_signal_schemas.py::test_reasoning_field -x` | ❌ Wave 0 |
| — | Post-validation (entry ±5%, SL 3×ATR, TP 5×ATR) | unit | `pytest tests/test_trading_signal_validation.py -x` | ❌ Wave 0 |
| — | Schema nesting validates correctly | unit | `pytest tests/test_trading_signal_schemas.py::test_full_batch_response -x` | ❌ Wave 0 |
| — | Migration 012 applies without error | manual-only | Run `alembic upgrade head` | — |
| — | Invalid signal stored with score=0 | unit | `pytest tests/test_trading_signal_validation.py::test_invalid_signal_storage -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `cd backend && python -m pytest tests/test_trading_signal_schemas.py tests/test_trading_signal_validation.py -x -q`
- **Per wave merge:** `cd backend && python -m pytest tests/ -v`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `tests/test_trading_signal_schemas.py` — covers PLAN-01 through PLAN-06 schema validation
- [ ] `tests/test_trading_signal_validation.py` — covers post-validation logic (entry/SL/TP bounds, R:R recalculation, invalid signal handling)

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | N/A — backend pipeline, no user auth change |
| V3 Session Management | no | N/A |
| V4 Access Control | no | N/A — same endpoints, no new permissions |
| V5 Input Validation | yes | Pydantic schema validation + post-validation for price targets |
| V6 Cryptography | no | N/A |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Prompt injection via ticker data | Tampering | Ticker data is from DB (trusted source), not user input. System instruction is hardcoded. |
| Hallucinated price targets | Information Disclosure | Post-validation rejects targets outside bounds (±5% entry, 3×ATR SL, 5×ATR TP) |
| Score=0 bypass for invalid signals | Tampering | CHECK constraint update is controlled via migration, not user-facing |

## Sources

### Primary (HIGH confidence)
- Codebase: `backend/app/services/ai_analysis_service.py` — all 4 analysis type patterns, _call_gemini, _run_batched_analysis, _store_analysis [VERIFIED: codebase]
- Codebase: `backend/app/schemas/analysis.py` — existing Pydantic schema patterns [VERIFIED: codebase]
- Codebase: `backend/app/models/ai_analysis.py` — AnalysisType enum, AIAnalysis model [VERIFIED: codebase]
- Codebase: `backend/app/scheduler/manager.py` — job chain: combined → signal_alerts [VERIFIED: codebase]
- Codebase: `backend/alembic/versions/002_analysis_tables.py` — score CHECK constraint [VERIFIED: codebase]
- Codebase: `backend/alembic/versions/003_sentiment_tables.py` — ALTER TYPE pattern [VERIFIED: codebase]
- Local test: google-genai 1.73.1 accepts nested 3-level Pydantic as response_schema [VERIFIED: local python test]
- Local test: GenerateContentConfig accepts max_output_tokens=32768 + ThinkingConfig(thinking_budget=2048) [VERIFIED: local python test]

### Secondary (MEDIUM confidence)
- CONTEXT.md decisions on batch size, schema design, migration strategy [VERIFIED: user decisions]

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new dependencies, all verified in codebase
- Architecture: HIGH — follows exact existing pattern for 4 analysis types
- Pitfalls: HIGH — score CHECK constraint verified in migration code; chain order verified in manager.py
- Schema: HIGH — nested Pydantic verified working with google-genai via local test

**Research date:** 2026-04-20
**Valid until:** 2026-05-20 (stable — no dependency changes expected)
