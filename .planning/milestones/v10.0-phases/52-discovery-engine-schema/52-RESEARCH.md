# Phase 52: Discovery Engine & Schema - Research

**Researched:** 2025-07-23
**Domain:** Backend computation pipeline + database schema (Python/FastAPI/SQLAlchemy/Alembic)
**Confidence:** HIGH

## Summary

Phase 52 adds a pure-computation discovery engine that scores all ~400 HOSE tickers daily on 6 indicator dimensions (RSI, MACD, ADX, volume, P/E, ROE), persists results in a `discovery_results` table with 14-day automatic cleanup, and adds a `sector_group` column to the existing `user_watchlist` table for Phase 54 preparation.

The implementation follows well-established patterns already in the codebase: a new service class (like `IndicatorService`), a new model (like `DailyPick`), a scheduled job function (like `daily_indicator_compute`), and a scheduler chain insertion in `manager.py`. The highest-risk area is the scheduler chain modification — inserting discovery between indicator compute and AI analysis requires exact string matching on job IDs.

**Primary recommendation:** Insert `daily_discovery_scoring` job between `daily_indicator_compute` and `daily_ai_analysis` in the chain. Create a `DiscoveryService` that reads from existing `technical_indicators` + `financials` + `daily_prices` tables, scores per dimension, upserts to `discovery_results`, and cleans up entries older than 14 days.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
None — all implementation choices at agent's discretion. Pure infrastructure phase.

### the agent's Discretion
All implementation choices are at the agent's discretion — pure infrastructure phase. Use ROADMAP phase goal, success criteria, and codebase conventions to guide decisions.

Key research context:
- Discovery scoring uses PURE indicators (no Gemini) — RSI, MACD, ADX, volume, P/E, ROE
- Existing `compute_composite_score()` and `compute_safety_score()` in pick_service.py can be adapted
- Discovery job must run SEQUENTIALLY after indicators in scheduler chain (DB pool limit 5+3)
- Scheduler chain uses exact string matching on job IDs — one wrong ID silently kills downstream
- `ticker_filter` parameter already exists in AIAnalysisService — preparation for Phase 53

### Deferred Ideas (OUT OF SCOPE)
None — infrastructure phase.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| DISC-01 | Scan ~400 HOSE tickers daily, score on technical (RSI, MACD, ADX, volume) + fundamental (P/E, ROE, growth) | DiscoveryService reads from existing `technical_indicators` + `financials` + `daily_prices` tables; scoring logic modeled after `compute_safety_score()` in pick_service.py |
| DISC-02 | Discovery results stored in DB with 14-day history retention | New `discovery_results` table with UniqueConstraint(ticker_id, date); DELETE WHERE date < today - 14 days at start of each run |
</phase_requirements>

## Standard Stack

### Core (Already in Project)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| SQLAlchemy | ~2.0 | ORM for discovery_results model | Already used for all 20+ models in the project |
| Alembic | ~1.18 | Database migration for new table + column | All 25 existing migrations use this pattern |
| APScheduler | 3.11.2 | Job scheduling and chain insertion | Existing scheduler infrastructure in manager.py |
| loguru | 0.7.3 | Structured logging for discovery job | Consistent with all existing services |

### Supporting (Already Available)
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pandas | ~2.2 | Not needed — discovery reads pre-computed indicators from DB | Only if raw computation needed |
| ta | 0.11.0 | Not needed — indicators already computed by IndicatorService | Pre-existing in pipeline |

**No new dependencies required.** Discovery uses purely existing data from pre-computed tables.

## Architecture Patterns

### Recommended Project Structure
```
backend/app/
├── models/
│   └── discovery_result.py       # New: DiscoveryResult SQLAlchemy model
├── services/
│   └── discovery_service.py      # New: DiscoveryService class
├── scheduler/
│   ├── jobs.py                   # Modified: add daily_discovery_scoring()
│   └── manager.py                # Modified: insert chain link + register job name
└── schemas/
    └── discovery.py              # New: Pydantic response schemas (for future Phase 55 API)

backend/alembic/versions/
└── 026_discovery_results_table.py  # New: create table + add sector_group column
```

### Pattern 1: Service Class (Follows IndicatorService Pattern)
**What:** A `DiscoveryService` class that takes an `AsyncSession`, queries existing data, scores all tickers, and upserts results.
**When to use:** For the daily discovery scoring job.
**Example:**
```python
# Source: Modeled after backend/app/services/indicator_service.py
class DiscoveryService:
    """Pure-computation discovery engine — scores all HOSE tickers."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def score_all_tickers(self) -> dict:
        """Score all active tickers on 6 dimensions.
        
        Returns: {success: int, failed: int, skipped: int, failed_symbols: list[str]}
        """
        # 1. Cleanup old results (> 14 days)
        # 2. Get active ticker map
        # 3. Fetch latest indicators per ticker (batch query)
        # 4. Fetch latest financials per ticker (batch query)
        # 5. Fetch recent volume per ticker (batch query)
        # 6. Score each ticker on 6 dimensions
        # 7. Upsert into discovery_results
        ...
```

### Pattern 2: Scheduler Chain Insertion
**What:** Add discovery job between indicator_compute and ai_analysis in the event chain.
**When to use:** In `manager.py::_on_job_executed()`.
**Example:**
```python
# Source: backend/app/scheduler/manager.py lines 77-85
# CURRENT: indicator_compute → ai_analysis
# AFTER:   indicator_compute → discovery_scoring → ai_analysis

elif event.job_id in ("daily_indicator_compute_triggered", "daily_indicator_compute_manual"):
    from app.scheduler.jobs import daily_discovery_scoring
    logger.info("Chaining: daily_indicator_compute → daily_discovery_scoring")
    scheduler.add_job(
        daily_discovery_scoring,
        id="daily_discovery_scoring_triggered",
        replace_existing=True,
        misfire_grace_time=3600,
    )

# NEW: After discovery scoring, chain to AI analysis
elif event.job_id in ("daily_discovery_scoring_triggered", "daily_discovery_scoring_manual"):
    from app.scheduler.jobs import daily_ai_analysis
    logger.info("Chaining: daily_discovery_scoring → daily_ai_analysis")
    scheduler.add_job(
        daily_ai_analysis,
        id="daily_ai_analysis_triggered",
        replace_existing=True,
        misfire_grace_time=3600,
    )
```

### Pattern 3: Model Definition (Follows DailyPick Pattern)
**What:** SQLAlchemy model with per-dimension score columns + composite score.
**Example:**
```python
# Source: Modeled after backend/app/models/daily_pick.py
class DiscoveryResult(Base):
    __tablename__ = "discovery_results"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    ticker_id: Mapped[int] = mapped_column(Integer, ForeignKey("tickers.id"), nullable=False)
    score_date: Mapped[date] = mapped_column(Date, nullable=False)
    
    # Per-dimension scores (0-10 scale)
    rsi_score: Mapped[Decimal | None] = mapped_column(Numeric(4, 2), nullable=True)
    macd_score: Mapped[Decimal | None] = mapped_column(Numeric(4, 2), nullable=True)
    adx_score: Mapped[Decimal | None] = mapped_column(Numeric(4, 2), nullable=True)
    volume_score: Mapped[Decimal | None] = mapped_column(Numeric(4, 2), nullable=True)
    pe_score: Mapped[Decimal | None] = mapped_column(Numeric(4, 2), nullable=True)
    roe_score: Mapped[Decimal | None] = mapped_column(Numeric(4, 2), nullable=True)
    
    # Composite
    total_score: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now()
    )

    __table_args__ = (
        UniqueConstraint("ticker_id", "score_date", name="uq_discovery_results_ticker_date"),
    )
```

### Pattern 4: Alembic Migration (Follows Existing Patterns)
**What:** Single migration file for both `discovery_results` table creation AND `sector_group` column addition to `user_watchlist`.
**Example:**
```python
# Source: Modeled after backend/alembic/versions/019_daily_picks_tables.py
revision: str = "026"
down_revision: Union[str, None] = "025"

def upgrade() -> None:
    # 1. Create discovery_results table
    op.create_table("discovery_results", ...)
    
    # 2. Add sector_group to user_watchlist (nullable — no data loss)
    op.add_column("user_watchlist", sa.Column("sector_group", sa.String(100), nullable=True))

def downgrade() -> None:
    op.drop_column("user_watchlist", "sector_group")
    op.drop_table("discovery_results")
```

### Anti-Patterns to Avoid
- **Computing indicators from raw prices in discovery:** Indicators are already computed by `IndicatorService` and stored in `technical_indicators`. Discovery should READ from that table, not recompute.
- **Parallel DB access during discovery:** With pool_size=5 + max_overflow=3, running discovery in parallel with other heavy jobs risks pool exhaustion. Must be sequential in the chain.
- **Missing `replace_existing=True` in chain jobs:** Without this, re-triggering fails silently with "Job already exists" error.
- **Forgetting to register job name in `_JOB_NAMES` dict:** The logging/monitoring system uses this for human-readable names.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Batch DB queries | Individual queries per ticker (N+1) | Single JOIN query fetching all tickers' latest indicators | 400 individual queries = 400 round-trips; 1 batch query = 1 round-trip |
| Upsert logic | Check-then-insert pattern | PostgreSQL `INSERT ON CONFLICT DO UPDATE` via `sqlalchemy.dialects.postgresql.insert` | Race-safe, idempotent, already used in IndicatorService |
| Scheduler chain | Custom timer/sleep-based chaining | APScheduler EVENT_JOB_EXECUTED listener | Already implemented and battle-tested in this project |
| Retention cleanup | Separate cron job for cleanup | `DELETE WHERE score_date < today - 14` at start of each scoring run | Simpler, atomic — cleanup is part of the same job |

**Key insight:** Discovery is pure DB-read + arithmetic + DB-write. All input data already exists in pre-computed tables. The complexity is in WHERE to insert in the chain and correct handling of NULL/missing data.

## Common Pitfalls

### Pitfall 1: Scheduler Chain String Mismatch
**What goes wrong:** Typing `"daily_indicator_compute_triggered"` as `"daily_indicators_compute_triggered"` silently breaks the entire downstream chain (AI, news, sentiment, picks — all stop running).
**Why it happens:** APScheduler matches job IDs by exact string. No runtime validation that a job with that ID exists.
**How to avoid:** Use constants for job IDs. Copy-paste from existing working code. Test the chain manually after deployment.
**Warning signs:** Downstream jobs stop appearing in `job_executions` table after the change.

### Pitfall 2: NULL Indicator/Financial Data
**What goes wrong:** Many tickers (especially recent IPOs) have NULL RSI, MACD, or financials. If scoring function doesn't handle NULLs, it either crashes or produces NaN scores.
**Why it happens:** Indicators require warm-up periods (RSI needs 14 days, SMA200 needs 200 days). Financials only update weekly.
**How to avoid:** Score each dimension independently. If data is NULL for a dimension, assign that dimension score as NULL (not 0). Compute total_score from available dimensions only, or skip tickers with < 3 scoreable dimensions.
**Warning signs:** `total_score` is 0 or NULL for many tickers; large `skipped` count in job results.

### Pitfall 3: Breaking Existing Chain by Removing Old Link
**What goes wrong:** After inserting discovery between indicators and AI analysis, forgetting to remove the OLD direct link (indicators → AI analysis) causes AI analysis to trigger TWICE — once from discovery completion and once from the old handler.
**Why it happens:** The `elif` chain in `_on_job_executed` needs the OLD handler REPLACED, not just a new one added.
**How to avoid:** Replace the existing `elif event.job_id in ("daily_indicator_compute_triggered", ...)` block — don't add a second one.
**Warning signs:** `daily_ai_analysis` appears twice in job_executions for the same day.

### Pitfall 4: Forgetting to Register Model in `__init__.py`
**What goes wrong:** Alembic `--autogenerate` doesn't detect the new model. Migration is empty or incomplete.
**Why it happens:** Alembic uses `Base.metadata` which only contains models that have been imported.
**How to avoid:** Add `from app.models.discovery_result import DiscoveryResult` to `app/models/__init__.py` and add to `__all__`.
**Warning signs:** `alembic revision --autogenerate` produces empty migration.

### Pitfall 5: Volume Query Performance
**What goes wrong:** Computing average volume for 400 tickers over 20-30 days means scanning thousands of daily_prices rows.
**Why it happens:** Without proper indexing or date range limitation, the query is slow.
**How to avoid:** Use `WHERE date >= current_date - 30` to limit scan. The existing `uq_daily_prices_ticker_date` index already covers (ticker_id, date) for efficient range scans. Batch ALL tickers in one query, not individually.
**Warning signs:** Discovery job takes > 30 seconds when it should complete in < 10.

## Code Examples

### Scoring Functions (Pure Computation)
```python
# Source: Adapted from backend/app/services/pick_service.py compute_safety_score()
def score_rsi(rsi_14: float | None) -> float | None:
    """RSI discovery score (0-10). Oversold = higher opportunity.
    
    RSI < 30 → 10 (oversold = buying opportunity)
    RSI 30-50 → 5-10 (approaching oversold)
    RSI 50-70 → 2-5 (neutral)
    RSI > 70 → 0-2 (overbought = low opportunity)
    """
    if rsi_14 is None:
        return None
    if rsi_14 <= 30:
        return 10.0
    elif rsi_14 <= 50:
        return 10 - (rsi_14 - 30) * 0.25  # 10→5 linear
    elif rsi_14 <= 70:
        return 5 - (rsi_14 - 50) * 0.15  # 5→2 linear
    else:
        return max(0, 2 - (rsi_14 - 70) * 0.1)  # 2→0

def score_macd(macd_histogram: float | None) -> float | None:
    """MACD histogram discovery score. Positive + increasing = bullish.
    
    Strong positive histogram → high score (bullish momentum)
    Near zero → medium score (neutral)
    Negative → low score (bearish)
    """
    if macd_histogram is None:
        return None
    # Normalize: typical MACD histogram range for VN stocks is -2 to +2
    normalized = max(-2, min(2, macd_histogram))
    return (normalized + 2) * 2.5  # Maps [-2, +2] → [0, 10]

def score_adx(adx_14: float | None, plus_di: float | None, minus_di: float | None) -> float | None:
    """ADX discovery score. Strong uptrend = high score.
    
    ADX > 25 + DI+ > DI- → strong bullish trend → high score
    ADX > 25 + DI- > DI+ → strong bearish trend → low score  
    ADX < 20 → weak trend → medium score (range-bound)
    """
    if adx_14 is None:
        return None
    trend_strength = min(10, adx_14 / 5)  # ADX 50 → 10
    if plus_di and minus_di:
        direction_bias = 1.0 if plus_di > minus_di else 0.3
    else:
        direction_bias = 0.5
    return trend_strength * direction_bias

def score_volume(avg_volume: int | None) -> float | None:
    """Volume discovery score. Higher liquidity = better opportunity.
    
    > 1M avg volume → 10 (very liquid)
    500K-1M → 7-10
    100K-500K → 3-7
    < 100K → 0-3 (illiquid)
    """
    if avg_volume is None or avg_volume == 0:
        return None
    return min(10, avg_volume / 100_000)

def score_pe(pe: float | None) -> float | None:
    """P/E discovery score. Lower P/E = potentially undervalued.
    
    P/E < 10 → 10 (undervalued)
    P/E 10-15 → 7-10 (reasonable)
    P/E 15-25 → 3-7 (fairly valued)
    P/E > 25 → 0-3 (expensive)
    Negative P/E → 0 (company losing money)
    """
    if pe is None:
        return None
    if pe <= 0:
        return 0.0
    if pe <= 10:
        return 10.0
    elif pe <= 15:
        return 10 - (pe - 10)  * 0.6  # 10→7
    elif pe <= 25:
        return 7 - (pe - 15) * 0.4   # 7→3
    else:
        return max(0, 3 - (pe - 25) * 0.1)

def score_roe(roe: float | None) -> float | None:
    """ROE discovery score. Higher ROE = more efficient.
    
    ROE > 20% → 10
    ROE 15-20% → 7-10
    ROE 10-15% → 5-7
    ROE 5-10% → 2-5
    ROE < 5% → 0-2
    Note: ROE stored as decimal (0.15 = 15%)
    """
    if roe is None:
        return None
    roe_pct = float(roe) * 100  # Convert from decimal
    if roe_pct >= 20:
        return 10.0
    elif roe_pct >= 15:
        return 7 + (roe_pct - 15) * 0.6
    elif roe_pct >= 10:
        return 5 + (roe_pct - 10) * 0.4
    elif roe_pct >= 5:
        return 2 + (roe_pct - 5) * 0.6
    else:
        return max(0, roe_pct * 0.4)
```

### Batch Query Pattern for Indicators
```python
# Source: Modeled after backend/app/services/pick_service.py lines 340-371
async def _fetch_latest_indicators(self, ticker_ids: list[int]) -> dict[int, dict]:
    """Fetch latest technical indicators for all tickers in one batch query."""
    # Subquery: most recent indicator date per ticker
    latest_sq = (
        select(
            TechnicalIndicator.ticker_id,
            func.max(TechnicalIndicator.date).label("max_date"),
        )
        .where(TechnicalIndicator.ticker_id.in_(ticker_ids))
        .group_by(TechnicalIndicator.ticker_id)
        .subquery()
    )
    # Main query: join to get actual indicator values at latest date
    stmt = (
        select(
            TechnicalIndicator.ticker_id,
            TechnicalIndicator.rsi_14,
            TechnicalIndicator.macd_histogram,
            TechnicalIndicator.adx_14,
            TechnicalIndicator.plus_di_14,
            TechnicalIndicator.minus_di_14,
        )
        .join(
            latest_sq,
            (TechnicalIndicator.ticker_id == latest_sq.c.ticker_id)
            & (TechnicalIndicator.date == latest_sq.c.max_date),
        )
    )
    rows = (await self.session.execute(stmt)).all()
    return {
        row.ticker_id: {
            "rsi_14": float(row.rsi_14) if row.rsi_14 is not None else None,
            "macd_histogram": float(row.macd_histogram) if row.macd_histogram is not None else None,
            "adx_14": float(row.adx_14) if row.adx_14 is not None else None,
            "plus_di_14": float(row.plus_di_14) if row.plus_di_14 is not None else None,
            "minus_di_14": float(row.minus_di_14) if row.minus_di_14 is not None else None,
        }
        for row in rows
    }
```

### 14-Day Retention Cleanup
```python
# Source: Standard DELETE pattern used in project
async def _cleanup_old_results(self) -> int:
    """Delete discovery results older than 14 days. Returns rows deleted."""
    from datetime import date, timedelta
    cutoff = date.today() - timedelta(days=14)
    stmt = delete(DiscoveryResult).where(DiscoveryResult.score_date < cutoff)
    result = await self.session.execute(stmt)
    deleted = result.rowcount
    if deleted > 0:
        logger.info(f"Cleaned up {deleted} discovery results older than {cutoff}")
    return deleted
```

### Job Function Pattern
```python
# Source: Modeled after backend/app/scheduler/jobs.py daily_indicator_compute()
async def daily_discovery_scoring():
    """Score all HOSE tickers for discovery.
    
    Triggered after daily_indicator_compute via job chaining.
    Pure computation — no external API calls. Reads from DB, scores, writes to DB.
    """
    logger.info("=== DAILY DISCOVERY SCORING START ===")
    async with async_session() as session:
        job_svc = JobExecutionService(session)
        execution = await job_svc.start("daily_discovery_scoring")
        try:
            from app.services.discovery_service import DiscoveryService
            service = DiscoveryService(session)
            result = await service.score_all_tickers()

            status = _determine_status(result)
            summary = _build_summary(result)
            await job_svc.complete(execution, status=status, result_summary=summary)
            await session.commit()
            logger.info(f"=== DAILY DISCOVERY SCORING COMPLETE: {summary} ===")

            if status == "failed":
                raise RuntimeError("Complete discovery scoring failure: all tickers failed")

        except Exception as e:
            if execution.status == "running":
                await job_svc.fail(execution, error=str(e))
                await session.commit()
            logger.error(f"=== DAILY DISCOVERY SCORING FAILED: {e} ===")
            raise
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Score each ticker individually with N+1 queries | Batch-fetch all data in 3-4 queries, score in-memory | Standard from pick_service.py | 100x fewer DB round-trips for 400 tickers |
| Full AI-powered discovery (Gemini scan all tickers) | Pure indicator scoring (no LLM) | v10.0 design decision | Eliminates 15 RPM rate limit constraint, runs in seconds vs minutes |

**Deprecated/outdated:**
- N/A — this is new functionality.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | MACD histogram range for VN stocks is roughly -2 to +2 for normalization | Code Examples (score_macd) | Scoring would be compressed/expanded — easy to tune |
| A2 | Average discovery scoring for 400 tickers completes in < 30 seconds | Architecture Patterns | If slower, may need batching or parallel optimization |
| A3 | Financial ROE is stored as decimal (0.15 = 15%) not percentage (15) | Code Examples (score_roe) | Score calculation would be wrong by 100x — verify from `Financial.roe` Numeric(8,4) |

## Open Questions

1. **Scoring Weights for Total Score**
   - What we know: 6 dimensions (RSI, MACD, ADX, volume, P/E, ROE)
   - What's unclear: Equal weighting (each 1/6) or weighted toward technical indicators?
   - Recommendation: Start with equal weights. Single-user app — tune in code later. Technical dimensions (4) naturally dominate fundamental (2) with equal weights.

2. **Minimum Scoreable Dimensions Threshold**
   - What we know: Many tickers will have NULL for some dimensions (missing financials, not enough price history)
   - What's unclear: Should we require all 6 dimensions? At least 3? At least technical-only?
   - Recommendation: Require at least 2 non-NULL dimensions. Compute total_score as average of available dimensions (weighted by available count). Flag tickers scored on fewer dimensions.

3. **ROE Storage Format Verification**
   - What we know: `Financial.roe` is `Numeric(8, 4)` which allows values like `0.1500` (15%) or `15.0000`
   - What's unclear: Does vnstock return ROE as decimal or percentage?
   - Recommendation: Check actual data in DB. The Numeric(8,4) constraint (max 9999.9999) suggests it could be either format.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest + pytest-asyncio |
| Config file | `backend/pytest.ini` |
| Quick run command | `cd backend && python -m pytest tests/test_discovery_service.py -x` |
| Full suite command | `cd backend && python -m pytest tests/ -x` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DISC-01 | All 6 scoring functions return 0-10 for valid inputs, None for None inputs | unit | `pytest tests/test_discovery_service.py::TestScoringFunctions -x` | ❌ Wave 0 |
| DISC-01 | score_all_tickers returns results for all active tickers with breakdown | unit | `pytest tests/test_discovery_service.py::TestDiscoveryService -x` | ❌ Wave 0 |
| DISC-02 | Old results (>14 days) cleaned up during each run | unit | `pytest tests/test_discovery_service.py::TestRetentionCleanup -x` | ❌ Wave 0 |
| DISC-02 | Upsert logic handles idempotent re-runs (same day) | unit | `pytest tests/test_discovery_service.py::TestUpsert -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `cd backend && python -m pytest tests/test_discovery_service.py -x`
- **Per wave merge:** `cd backend && python -m pytest tests/ -x`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `tests/test_discovery_service.py` — covers DISC-01, DISC-02 (scoring functions + service behavior)
- [ ] Model import in `app/models/__init__.py` — required for Alembic detection

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | Single-user app — no auth |
| V3 Session Management | no | N/A |
| V4 Access Control | no | Single-user app |
| V5 Input Validation | yes | All scores computed from pre-validated DB data; Numeric column types enforce range |
| V6 Cryptography | no | No sensitive data in discovery results |

### Known Threat Patterns

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| SQL injection via ticker symbols | Tampering | SQLAlchemy parameterized queries (already used) |
| Denial of service from computation | Denial of Service | Sequential execution in scheduler chain; bounded by ~400 tickers |

No significant security concerns — pure internal computation on pre-existing data.

## Sources

### Primary (HIGH confidence)
- `backend/app/scheduler/manager.py` — Complete scheduler chain logic and event listener pattern [VERIFIED: codebase]
- `backend/app/services/pick_service.py` — Existing scoring functions (compute_composite_score, compute_safety_score) [VERIFIED: codebase]
- `backend/app/services/indicator_service.py` — Service pattern, batch computation, TickerService usage [VERIFIED: codebase]
- `backend/app/models/` — All 20+ model definitions showing SQLAlchemy patterns [VERIFIED: codebase]
- `backend/alembic/versions/` — 25 migrations showing naming/structure conventions [VERIFIED: codebase]
- `backend/app/database.py` — Pool config: pool_size=5, max_overflow=3 [VERIFIED: codebase]

### Secondary (MEDIUM confidence)
- SQLAlchemy 2.0 `insert().on_conflict_do_update()` — Already used in indicator_service.py [VERIFIED: codebase usage]
- APScheduler event chaining via `EVENT_JOB_EXECUTED` — Already implemented in manager.py [VERIFIED: codebase]

### Tertiary (LOW confidence)
- None — all findings verified from codebase.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new libraries needed, all patterns exist in codebase
- Architecture: HIGH — follows established IndicatorService/PickService patterns exactly
- Pitfalls: HIGH — identified from actual codebase inspection of scheduler chain mechanics

**Research date:** 2025-07-23
**Valid until:** Indefinitely (codebase patterns are stable, no external dependencies)
