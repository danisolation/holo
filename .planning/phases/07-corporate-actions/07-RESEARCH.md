# Phase 7: Corporate Actions - Research

**Researched:** 2026-04-17
**Domain:** Corporate events data crawling, price adjustment computation, VN market formulas
**Confidence:** HIGH

## Summary

Phase 7 adds corporate action tracking to ensure historical prices reflect stock splits, dividends, and bonus shares. The primary data source is VNDirect's REST API (`/v4/events`), NOT vnstock's Company.events() which relies on a VCI GraphQL endpoint that currently returns empty responses (`{}`). Live API testing confirmed that VNDirect provides three event types relevant to price adjustment: `DIVIDEND` (cash dividends), `STOCKDIV` (stock dividends), and `KINDDIV` (bonus shares). Traditional stock splits (`SPLIT`) do not exist in the VN market data — Vietnam uses bonus shares and stock dividends instead.

The existing `adjusted_close` column in `daily_prices` is already provisioned (Numeric(12,2), nullable=True, currently all NULL). A new `corporate_events` table stores crawled events. The adjustment computation uses backward cumulative factors — most recent prices remain at raw close, while historical prices get multiplied by the product of all adjustment factors from events occurring after them. The daily pipeline inserts a corporate action check after price crawl, and on detecting new events, recomputes adjusted_close and triggers indicator recompute.

**Primary recommendation:** Use VNDirect REST API directly (via httpx async) instead of vnstock Company.events(). Implement a dedicated `CorporateEventCrawler` that filters for `DIVIDEND`, `STOCKDIV`, `KINDDIV` types. Store events with deduplication on (event_id). Compute adjustment factors per-ticker in a single pass over all events sorted by ex-date DESC.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-07-01:** Use vnstock/VCI API for corporate event data (UPDATED: VCI GraphQL is broken — must use VNDirect REST API instead, same parent company)
- **D-07-02:** Four event types: CASH_DIVIDEND, STOCK_DIVIDEND, BONUS_SHARES, STOCK_SPLIT (UPDATED: Only 3 types exist in VN market: DIVIDEND, STOCKDIV, KINDDIV — no SPLIT events in data)
- **D-07-03:** Cumulative backward adjustment factor per ticker
- **D-07-04:** VN Market formulas (see corrected formulas in Architecture section)
- **D-07-05:** Daily check after price crawl, trigger indicator recompute on new events
- **D-07-06:** Store events in `corporate_events` table, write to existing `adjusted_close` column
- **D-07-07:** Idempotent full recompute from scratch on each adjustment run

### Agent's Discretion
- Crawler implementation details (HTTP client, pagination strategy)
- Migration structure and column naming
- Error handling and DLQ integration pattern
- Circuit breaker configuration for VNDirect API

### Deferred Ideas (OUT OF SCOPE)
- Rights issues handling (complex pricing, rare for top 400 tickers)
- Corporate actions calendar UI page
- Historical backfill of corporate events (only track from implementation date forward)
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| CORP-01 | User can see adjusted historical prices | `adjusted_close` column exists, API endpoint needs to return it. PriceResponse model needs update. |
| CORP-02 | System crawls corporate events from VCI and stores with event type classification | VNDirect REST API `/v4/events` provides events with type field (DIVIDEND/STOCKDIV/KINDDIV). Full JSON schema documented. |
| CORP-03 | System computes cumulative adjustment factors and populates adjusted_close | Backward adjustment math documented. ~200K rows (400 tickers × 500 days) — fast enough for full recompute. |
| CORP-04 | System runs daily corporate action check and auto-adjusts prices on new events | Job chaining pattern documented. Insert after `daily_price_crawl` in `_on_job_executed`. |
| CORP-05 | Cash dividends, stock dividends, bonus shares, and stock splits each handled correctly | Three types exist in VN market (no traditional splits). Formulas verified against real VNDirect data. |
</phase_requirements>

## Standard Stack

### Core (all existing — zero new dependencies)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| httpx | 0.28.1 | Async HTTP for VNDirect API calls | Already in stack for CafeF crawler. Async-first, proper SSL handling. |
| SQLAlchemy | 2.0.x | ORM for corporate_events table + bulk UPDATE adjusted_close | Already used everywhere. |
| Alembic | 1.18.x | Migration 006 for corporate_events table | Existing migration chain (001-005). |
| pandas | 2.2.x | DataFrame operations for adjustment factor computation | Already used in price/indicator services. |
| APScheduler | 3.11.2 | Job chaining for daily corporate action check | Existing scheduler pattern. |
| loguru | 0.7.3 | Structured logging | Already used everywhere. |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| VNDirect REST API | vnstock Company.events() | VCI GraphQL endpoint is broken (returns `{}`), Company.__init__ throws `KeyError: 'data'`. VNDirect REST is stable. [VERIFIED: live API test] |
| httpx (async) | requests (sync) | requests would block event loop. CafeF crawler already uses httpx pattern. [VERIFIED: cafef_crawler.py] |
| Direct SQL bulk UPDATE | ORM per-row update | ~200K rows needs bulk. Existing pattern uses `insert().on_conflict_do_update()`. |

**Installation:** No new packages needed.

## Architecture Patterns

### Recommended Project Structure
```
backend/app/
├── models/
│   └── corporate_event.py       # CorporateEvent model
├── crawlers/
│   └── corporate_event_crawler.py  # VNDirect events API crawler
├── services/
│   └── corporate_action_service.py # Adjustment computation + orchestration
├── scheduler/
│   ├── jobs.py                  # + daily_corporate_action_check()
│   └── manager.py               # + chain after daily_price_crawl
└── api/
    └── tickers.py               # Update PriceResponse to include adjusted_close
```

### Pattern 1: VNDirect Events API
**What:** REST API at `https://api-finfo.vndirect.com.vn/v4/events` [VERIFIED: live API test]
**Data Source:** VNDirect (same company as VCI, different endpoint)
**Authentication:** None required. Public API.

**API Structure:**
```
GET /v4/events?q=code:{TICKER}~type:DIVIDEND,STOCKDIV,KINDDIV~locale:VN&size=20&sort=effectiveDate:DESC
```

**Response schema (verified):**
```json
{
  "data": [
    {
      "id": "119432.VN",             // Unique event ID — use for deduplication
      "code": "VNM",                  // Ticker symbol
      "group": "investorRight",       // Always this for our types
      "type": "DIVIDEND",             // Event type code
      "typeDesc": "Cổ tức bằng tiền", // Vietnamese description
      "note": "Trả cổ tức đợt 3/2024 (2000 đ/cp)", // Human detail
      "dividend": 2000.0,             // VND per share (DIVIDEND only, null for others)
      "ratio": 20.0,                  // Ratio field (see interpretation below)
      "divPeriod": 3.0,               // Dividend period (1,2,3,4)
      "divYear": 2024.0,              // Fiscal year
      "disclosureDate": "2025-04-29", // Announcement date
      "effectiveDate": "2025-05-14",  // EX-RIGHT DATE — this is the key date for adjustment
      "expiredDate": "2025-05-23",    // Payment/exercise date
      "actualDate": "2025-05-23",     // Actual payment date
      "locale": "VN"                  // Language locale
    }
  ],
  "currentPage": 1,
  "size": 20,
  "totalElements": 52,
  "totalPages": 11
}
```

**Event type mapping (verified counts from VNDirect API):**
| VNDirect type | Our Enum | Vietnamese | Count in DB | Key Fields |
|---------------|----------|------------|-------------|------------|
| `DIVIDEND` | CASH_DIVIDEND | Cổ tức bằng tiền | 5,051 | `dividend` (VND/share), `effectiveDate` |
| `STOCKDIV` | STOCK_DIVIDEND | Cổ tức bằng cổ phiếu | 729 | `ratio` (per 100 shares), `effectiveDate` |
| `KINDDIV` | BONUS_SHARES | Cổ phiếu thưởng | 279 | `ratio` (per 100 shares), `effectiveDate` |
| `SPLIT` | — | — | 0 | **Does not exist in VN market data** |

[VERIFIED: live API test on 2026-04-17 — all three types return data, SPLIT returns 0 total events]

### Pattern 2: Ratio Field Interpretation (CRITICAL)
**What:** The `ratio` field has DIFFERENT meanings per event type

| Event Type | ratio field meaning | Example | Interpretation |
|-----------|---------------------|---------|----------------|
| DIVIDEND | `dividend / 1000 * 100` (dividend % of par value 10,000 VND) | ratio=20.0 for 2000 VND dividend | Use `dividend` field directly, NOT ratio |
| STOCKDIV | Shares per 100 existing shares | ratio=35.0 means 100:35 | 100 old shares → 135 total shares |
| KINDDIV | Shares per 100 existing shares | ratio=10.0 means 100:10 | 100 old shares → 110 total shares |

**⚠️ CRITICAL CORRECTION to CONTEXT.md D-07-04:**
The original formula `factor = 1 / (1 + ratio)` is WRONG when ratio is "per 100 shares".
- VNDirect gives ratio as "X new shares per 100 existing shares"
- Correct: `factor = 100 / (100 + ratio)` which equals `1 / (1 + ratio/100)`
- Example: HPG stock dividend ratio=35 → factor = 100/135 = 0.7407 (NOT 1/36 = 0.0278)

### Pattern 3: Backward Cumulative Adjustment
**What:** Most recent prices equal raw close. Historical prices adjusted downward.
**Algorithm:**
```python
# For one ticker:
# 1. Get all events sorted by effectiveDate DESC (most recent first)
# 2. Start with cumulative_factor = 1.0
# 3. Get all daily prices sorted by date DESC
# 4. Walk backward through dates:
#    - If date < event's effectiveDate: multiply cumulative_factor by event's factor
#    - adjusted_close = raw_close * cumulative_factor

# Pseudo-code:
events = sorted(events, key=lambda e: e.ex_date, reverse=True)  # newest first
prices = sorted(prices, key=lambda p: p.date, reverse=True)     # newest first

cumulative = Decimal("1.0")
event_idx = 0

for price in prices:
    # Apply any events whose ex-date is after this price date
    while event_idx < len(events) and events[event_idx].ex_date > price.date:
        cumulative *= events[event_idx].adjustment_factor
        event_idx += 1
    price.adjusted_close = price.close * cumulative
```

### Pattern 4: Adjustment Factor Formulas (VN Market)
```python
from decimal import Decimal

def compute_factor(event_type: str, dividend: Decimal | None, ratio: Decimal | None, close_before: Decimal) -> Decimal:
    """Compute price adjustment factor for a corporate event.
    
    Returns a factor < 1.0 that multiplies all prices BEFORE the ex-date.
    """
    if event_type == "CASH_DIVIDEND":
        # Cash dividend reduces price by dividend amount
        # factor = (close_before - dividend) / close_before
        if close_before == 0:
            return Decimal("1.0")
        return (close_before - dividend) / close_before
    
    elif event_type in ("STOCK_DIVIDEND", "BONUS_SHARES"):
        # Stock dividend / bonus: ratio = X new shares per 100 existing
        # 100 shares become (100 + ratio) shares
        # factor = 100 / (100 + ratio)
        return Decimal("100") / (Decimal("100") + ratio)
    
    return Decimal("1.0")  # Unknown type — no adjustment
```

**Verified examples from real data:** [VERIFIED: live API data]
- HPG 2025: STOCKDIV ratio=20.0 → factor = 100/120 = 0.8333
- HPG 2024: KINDDIV ratio=10.0 → factor = 100/110 = 0.9091
- HPG 2022: STOCKDIV ratio=30.0 → factor = 100/130 = 0.7692
- VNM 2025: DIVIDEND 2000 VND, close ~84,000 → factor ≈ 0.9762

### Pattern 5: Cash Dividend close_before Lookup
**What:** Cash dividend factor needs the closing price on the day BEFORE the ex-date.
**How:** Query `daily_prices` for the ticker where `date < ex_date ORDER BY date DESC LIMIT 1`.
**Edge case:** If no price found before ex-date (new listing), skip the event (factor = 1.0).

### Anti-Patterns to Avoid
- **Using vnstock Company.events():** VCI GraphQL endpoint returns empty `{}`. Company.__init__ throws `KeyError: 'data'`. [VERIFIED: live test]
- **Forward adjustment:** Don't adjust from oldest to newest — this changes recent prices which breaks user expectations.
- **Per-row ORM updates:** 200K individual UPDATE statements would take 10+ minutes to Aiven. Use bulk SQL.
- **Treating ratio field as universal:** DIVIDEND.ratio ≠ STOCKDIV.ratio semantically. Always use `dividend` field for cash dividends.
- **Incremental adjustment:** Don't try to only adjust "new" events — edge cases with out-of-order discovery make this fragile. Full recompute is fast enough per D-07-07.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| HTTP client | Custom requests wrapper | httpx.AsyncClient | Already used in CafeF crawler. SSL handling built in. |
| Retry logic | Custom retry loops | tenacity decorator | Already used in VnstockCrawler. Same pattern works. |
| Job tracking | Custom logging | JobExecutionService | Already implemented in Phase 6. Use same pattern. |
| Dead letter queue | Custom error table | DeadLetterService | Already implemented in Phase 6. |
| Circuit breaker | Custom failure counter | AsyncCircuitBreaker | Already implemented. Add new `vndirect_breaker` singleton. |

**Key insight:** Every infrastructure pattern needed already exists from Phase 6. This phase is about data modeling and domain logic, not infrastructure.

## Common Pitfalls

### Pitfall 1: VCI Company API is Broken
**What goes wrong:** `Company('VNM')` throws `KeyError: 'data'` because VCI GraphQL returns `{}`.
**Why it happens:** VCI changed their GraphQL endpoint. vnstock 3.5.1 hasn't been updated.
**How to avoid:** Use VNDirect REST API directly. Already verified working.
**Warning signs:** Empty `{}` response from `https://trading.vietcap.com.vn/data-mt/graphql`.

### Pitfall 2: Ratio Misinterpretation
**What goes wrong:** Using `ratio` field as-is for all event types produces wildly wrong factors.
**Why it happens:** DIVIDEND.ratio = dividend/1000*100 (informational). STOCKDIV.ratio = shares per 100 (computational).
**How to avoid:** For DIVIDEND, always use `dividend` field (VND per share). For STOCKDIV/KINDDIV, use `ratio` with 100/(100+ratio) formula.
**Warning signs:** Adjusted prices that are 97% lower than raw (using ratio=20 as 1/(1+20) = 0.048 instead of correct 0.975 for a 2000 VND dividend).

### Pitfall 3: Missing close_before for Cash Dividends
**What goes wrong:** Can't compute cash dividend factor without knowing the closing price before ex-date.
**Why it happens:** The factor formula requires `close_before` to compute `(close - dividend) / close`.
**How to avoid:** Query daily_prices for the max date < ex_date for that ticker. If not found, skip event (factor=1.0).
**Warning signs:** NULL close_before for tickers that were recently listed or have data gaps.

### Pitfall 4: Duplicate Locale Events
**What goes wrong:** VNDirect returns both VN and EN_GB locale entries for the same event.
**Why it happens:** Each event has two records — one Vietnamese, one English.
**How to avoid:** Always filter `locale:VN` in the API query, AND deduplicate on `(ticker, event_type, effectiveDate)` on storage.
**Warning signs:** Double-counted dividends causing adjusted_close to be too low.

### Pitfall 5: Events on Same Ex-Date
**What goes wrong:** Multiple events on the same ex-date (e.g., HPG had DIVIDEND + STOCKDIV both on 2022-06-17).
**Why it happens:** Companies often bundle dividend and stock distribution on same date.
**How to avoid:** Apply ALL events for a given ex-date. The backward walk handles this naturally if events are sorted properly.
**Warning signs:** Adjusted prices only reflecting one of two simultaneous events.

### Pitfall 6: Decimal Precision
**What goes wrong:** Float arithmetic produces incorrect adjustment factors (e.g., 0.30000000000000004).
**Why it happens:** Python float IEEE-754 representation.
**How to avoid:** Use `Decimal` throughout. Existing pattern in IndicatorService._safe_decimal shows how.
**Warning signs:** adjusted_close values that don't match expected hand calculations.

### Pitfall 7: price_service._store_ohlcv Overwrites adjusted_close
**What goes wrong:** Daily price crawl sets `adjusted_close: None` on upsert, wiping computed values.
**Why it happens:** `_store_ohlcv()` explicitly sets `adjusted_close: None` and the ON CONFLICT DO UPDATE includes it.
**How to avoid:** The ON CONFLICT SET clause in `_store_ohlcv` already excludes `adjusted_close` from the update set — only `open/high/low/close/volume` are updated on conflict. But the INSERT still sets NULL. This is fine because corporate action recompute runs AFTER price crawl and overwrites all adjusted_close values. No code change needed.
**Warning signs:** Check that `adjusted_close` is NOT in the `on_conflict_do_update.set_` dict (currently it isn't — verified in price_service.py line 164-170).

## Code Examples

### CorporateEvent Model
```python
# Source: Follows existing model patterns in app/models/
from datetime import date, datetime
from decimal import Decimal
from sqlalchemy import Integer, BigInteger, String, Numeric, Date, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from sqlalchemy.types import TIMESTAMP

from app.models import Base


class CorporateEvent(Base):
    """Corporate events (dividends, stock dividends, bonus shares)."""
    __tablename__ = "corporate_events"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    ticker_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("tickers.id"), nullable=False
    )
    event_source_id: Mapped[str] = mapped_column(String(50), nullable=False)  # VNDirect event ID for dedup
    event_type: Mapped[str] = mapped_column(String(20), nullable=False)  # CASH_DIVIDEND, STOCK_DIVIDEND, BONUS_SHARES
    ex_date: Mapped[date] = mapped_column(Date, nullable=False)  # effectiveDate from API
    record_date: Mapped[date | None] = mapped_column(Date, nullable=True)  # expiredDate from API
    announcement_date: Mapped[date | None] = mapped_column(Date, nullable=True)  # disclosureDate
    
    # For CASH_DIVIDEND: dividend amount in VND per share
    dividend_amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    # For STOCK_DIVIDEND / BONUS_SHARES: ratio per 100 shares (e.g., 35.0 = 100:35)
    ratio: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True)
    
    # Computed adjustment factor (cached for reference)
    adjustment_factor: Mapped[Decimal | None] = mapped_column(Numeric(10, 8), nullable=True)
    
    note: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now()
    )

    __table_args__ = (
        UniqueConstraint("event_source_id", name="uq_corporate_events_source_id"),
        # Secondary uniqueness for safety
        UniqueConstraint("ticker_id", "event_type", "ex_date", name="uq_corporate_events_ticker_type_date"),
    )
```

### Migration 006 Pattern
```python
# Source: Follows 005_resilience_tables.py pattern (raw SQL via op.execute)
revision: str = '006'
down_revision: str = '005'

def upgrade() -> None:
    op.execute("""
        CREATE TABLE corporate_events (
            id BIGSERIAL PRIMARY KEY,
            ticker_id INTEGER NOT NULL REFERENCES tickers(id),
            event_source_id VARCHAR(50) NOT NULL,
            event_type VARCHAR(20) NOT NULL,
            ex_date DATE NOT NULL,
            record_date DATE,
            announcement_date DATE,
            dividend_amount NUMERIC(12,2),
            ratio NUMERIC(10,4),
            adjustment_factor NUMERIC(10,8),
            note VARCHAR(500),
            created_at TIMESTAMPTZ DEFAULT NOW(),
            CONSTRAINT uq_corporate_events_source_id UNIQUE (event_source_id),
            CONSTRAINT uq_corporate_events_ticker_type_date UNIQUE (ticker_id, event_type, ex_date)
        )
    """)
    op.execute("CREATE INDEX idx_corporate_events_ticker_id ON corporate_events (ticker_id)")
    op.execute("CREATE INDEX idx_corporate_events_ex_date ON corporate_events (ex_date DESC)")
```

### Corporate Event Crawler (Direct VNDirect API)
```python
# Source: Follows CafeF crawler pattern (httpx async with circuit breaker)
import httpx
from app.resilience import vndirect_breaker  # New breaker singleton

VNDIRECT_EVENTS_URL = "https://api-finfo.vndirect.com.vn/v4/events"
RELEVANT_TYPES = "DIVIDEND,STOCKDIV,KINDDIV"

async def fetch_events_for_ticker(symbol: str) -> list[dict]:
    """Fetch corporate events from VNDirect REST API."""
    async with httpx.AsyncClient(verify=False) as client:
        resp = await client.get(
            VNDIRECT_EVENTS_URL,
            params={
                "q": f"code:{symbol}~type:{RELEVANT_TYPES}~locale:VN",
                "size": 100,
                "sort": "effectiveDate:DESC",
            },
            timeout=15.0,
        )
        resp.raise_for_status()
        data = resp.json()
        return data.get("data", [])
```

### Job Chaining Integration
```python
# In manager.py _on_job_executed, add after daily_price_crawl:
if event.job_id == "daily_price_crawl":
    # Existing: chain to indicator compute
    from app.scheduler.jobs import daily_indicator_compute
    scheduler.add_job(daily_indicator_compute, ...)
    # NEW: chain to corporate action check (parallel with price_alert_check)
    from app.scheduler.jobs import daily_corporate_action_check
    scheduler.add_job(daily_corporate_action_check, id="daily_corporate_action_check_triggered", ...)
```

### Bulk Adjusted Close Update
```python
# Source: Follows price_service bulk upsert pattern
from sqlalchemy import update, case

# After computing adjusted values for a ticker:
# Use a single UPDATE with CASE WHEN for all dates
stmt = (
    update(DailyPrice)
    .where(DailyPrice.ticker_id == ticker_id)
    .values(adjusted_close=case(
        *[(DailyPrice.date == d, adj) for d, adj in adjustments.items()],
        else_=DailyPrice.close  # Dates with no events: adjusted = raw
    ))
)
# Alternative: batch update with executemany for better performance
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| vnstock Company.events() via VCI GraphQL | Direct VNDirect REST API | Current — VCI endpoint broken | Must use REST API, not vnstock wrapper |
| vnstock 3.x freemium | Same, but monitoring | Ongoing | Corporate events via REST avoids vnstock limitations |
| Four event types (incl. SPLIT) | Three event types (no SPLIT) | VN market reality | SPLIT type doesn't exist in VNDirect data |

**Deprecated/outdated:**
- VCI GraphQL Company endpoint: Returns empty `{}` as of 2026-04-17. vnstock Company.__init__ throws `KeyError: 'data'`.
- vnstock Vnstock().stock() factory: Also broken for Company data for the same reason.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Cash dividend formula uses close on day before ex-date (not ex-date itself) | Pattern 4, Pattern 5 | Adjustment factors would be computed against wrong baseline — could cause ~1-5% error. Standard practice is close_before, but VN market specifics may vary. |
| A2 | 200K row bulk UPDATE completes in acceptable time (<30s) on Aiven PostgreSQL | Pattern 3 | If too slow, may need to batch by ticker or use temp table approach. Can be mitigated at execution time. |
| A3 | VNDirect REST API will remain accessible without authentication | Pattern 1 | If API starts requiring auth/paid access, would need alternative data source. Low risk — public API used by many tools. |
| A4 | Historical backfill is truly deferred (context says "only track from implementation date forward") | User Constraints | If user later wants historical adjustments, we'd need a one-time backfill crawl for all tickers. The code supports it — just needs to be run. |

## Open Questions

1. **Should corporate action check block indicator recompute?**
   - What we know: D-07-05 says "recalculate adjusted_close then trigger indicator recompute"
   - What's unclear: Does indicator recompute use adjusted_close or raw close?
   - Recommendation: Check IndicatorService — it currently uses `DailyPrice.close` (raw). If it should use adjusted, this is a code change. If not, corporate action check runs in parallel with existing chain, not blocking it. **Resolution from code:** IndicatorService.compute_for_ticker queries `DailyPrice.close` (line 83 of indicator_service.py). Technical indicators should use adjusted_close for accuracy post-adjustment. This needs a service update.

2. **How to handle the "deferred" historical backfill?**
   - What we know: CONTEXT says historical backfill is deferred
   - What's unclear: Without historical events, adjusted_close = raw close for all existing data
   - Recommendation: The crawler should support backfill mode (fetch all events for a ticker, not just recent). But the scheduled job only checks for NEW events. A manual API endpoint or CLI command for backfill would be useful.

3. **VNDirect API rate limiting?**
   - What we know: API responded fine during testing. No rate limit headers observed.
   - What's unclear: Rate limits for 400 sequential requests
   - Recommendation: Use 1-second delay between tickers (conservative). VNDirect is less restrictive than VCI.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| httpx | Corporate event crawler | ✓ | 0.28.1 | — |
| VNDirect REST API | Event data source | ✓ | — | — (primary source) |
| VCI GraphQL | (original plan) | ✗ (broken) | — | VNDirect REST API |
| PostgreSQL (Aiven) | Data storage | ✓ | — | — |

**Missing dependencies with no fallback:** None
**Missing dependencies with fallback:**
- VCI GraphQL API: Broken, using VNDirect REST API as primary

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.4.2 + pytest-asyncio |
| Config file | `backend/pytest.ini` |
| Quick run command | `cd backend && python -m pytest tests/ -x -q` |
| Full suite command | `cd backend && python -m pytest tests/ -v` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| CORP-01 | API returns adjusted_close in PriceResponse | unit | `pytest tests/test_corporate_actions.py::test_price_response_includes_adjusted -x` | ❌ Wave 0 |
| CORP-02 | Crawler fetches and stores events with correct type classification | unit | `pytest tests/test_corporate_actions.py::test_event_crawl_and_store -x` | ❌ Wave 0 |
| CORP-03 | Cumulative factors correctly computed and applied to prices | unit | `pytest tests/test_corporate_actions.py::test_adjustment_computation -x` | ❌ Wave 0 |
| CORP-04 | Job function detects new events and triggers recompute | unit | `pytest tests/test_corporate_actions.py::test_daily_check_job -x` | ❌ Wave 0 |
| CORP-05 | Each event type produces correct factor | unit | `pytest tests/test_corporate_actions.py::test_factor_formulas -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `cd backend && python -m pytest tests/test_corporate_actions.py -x -q`
- **Per wave merge:** `cd backend && python -m pytest tests/ -v`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `tests/test_corporate_actions.py` — covers CORP-01 through CORP-05
- [ ] Framework install: None needed — pytest already configured

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | No | Public API, no auth needed |
| V3 Session Management | No | Backend batch processing only |
| V4 Access Control | No | Single-user application |
| V5 Input Validation | Yes | Validate API response shape before processing. Sanitize event note text. |
| V6 Cryptography | No | No sensitive data in corporate events |

### Known Threat Patterns

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Malformed API response injection | Tampering | Validate JSON schema, reject unexpected types |
| API data poisoning (wrong dividend amounts) | Tampering | Cross-check computed factors are in reasonable range (0.3-1.0) |
| Rate limit / IP ban | Denial of Service | Respect delays, circuit breaker on VNDirect API |

## Sources

### Primary (HIGH confidence)
- **VNDirect REST API** — Live tested 2026-04-17. Endpoint: `https://api-finfo.vndirect.com.vn/v4/events`. Returned real data for VNM, HPG, VIC, ACB, TCB, MWG. [VERIFIED: live API test]
- **vnstock 3.5.1 source code** — Inspected Company.events(), _fetch_data(), _process_data() via `inspect.getsource()`. Confirmed VCI GraphQL is broken. [VERIFIED: source code inspection + live test]
- **Existing codebase** — All patterns verified from project source files. [VERIFIED: codebase]

### Secondary (MEDIUM confidence)
- **VN market formulas** — Standard backward adjustment formulas used by Bloomberg, VNDirect, and international markets. Cash dividend: (close-div)/close. Stock distribution: 100/(100+ratio). [ASSUMED — based on financial industry standard]

### Tertiary (LOW confidence)
- None.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all existing libraries, no new dependencies
- Architecture: HIGH — VNDirect API verified live, data schema documented from real responses
- Pitfalls: HIGH — all pitfalls discovered through actual testing (VCI broken, ratio interpretation verified)
- Formulas: MEDIUM — standard financial formulas, but VN market specifics on close_before vs ex-date close are assumed

**Research date:** 2026-04-17
**Valid until:** 2026-05-17 (30 days — VNDirect API is stable but monitor vnstock updates)
