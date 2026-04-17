# Technology Stack — v1.1 Reliability & Portfolio

**Project:** Holo — Stock Intelligence Platform
**Milestone:** v1.1 Reliability & Portfolio
**Researched:** 2026-04-16
**Overall confidence:** HIGH

## Executive Summary

v1.1 needs **zero new backend Python libraries** and only **3 small frontend additions**. The existing stack (FastAPI + SQLAlchemy + tenacity + google-genai + vnstock) already covers corporate actions data sourcing, retry/backoff, and structured AI output. New features are implemented as **business logic + new DB models**, not new dependencies.

The key discovery: vnstock 3.5.1's `Company.events()` already returns corporate action data (splits, dividends, bonus, rights) with `eventListCode`, `ratio`, `value`, `recordDate`, `exrightDate` — no scraping or alternative data source needed.

Circuit breaker does NOT need a library (aiobreaker 1.2.0 is Tornado-legacy with only 3 releases ever; pybreaker 1.4.1 has no native asyncio). A ~30-line custom async circuit breaker is more maintainable.

Prometheus/Grafana is overkill for a single-user app. System health monitoring is a `job_runs` DB table + dashboard page using existing recharts.

---

## What the Existing Stack Already Covers

Before listing additions, it's critical to map what's already handled:

| v1.1 Feature | Covered By (Existing) | How |
|---|---|---|
| Corporate actions data | **vnstock 3.5.1** `Company.events()` | Returns `eventListCode`, `ratio`, `value`, `recordDate`, `exrightDate` via VCI GraphQL |
| Price adjustment math | **Python `decimal.Decimal`** + existing `adjusted_close` column | Multiply/divide by ratio — pure arithmetic |
| FIFO cost basis | **Python `decimal.Decimal`** | Sort trades by date, dequeue oldest lots on sell |
| Realized/unrealized P&L | **SQLAlchemy 2.0** queries + Python | Query current prices vs cost basis |
| AI structured output | **google-genai** `response_schema` + Pydantic | Already using `response_schema=PydanticModel` in `_call_gemini()` |
| AI system instructions | **google-genai** `system_instruction` param | Available in `GenerateContentConfig` — currently unused, prompts are inline |
| Retry with backoff | **tenacity 9.1.4** | Already decorating `_call_gemini()` with `@retry` |
| Rate limit handling | **Custom batch loop** in `_run_batched_analysis()` | Already handles 429s with progressive backoff |
| DB migrations | **Alembic 1.18** | New tables (corporate_actions, trades, job_runs) are standard migrations |
| Health dashboard charts | **Recharts 3.x** | Bar charts for error rates, area charts for data freshness |
| Health dashboard UI | **shadcn/ui 4.x** + **@tanstack/react-table** | Cards for status, tables for job history |
| Portfolio data tables | **@tanstack/react-table 8.x** | Holdings view, trade history |
| Portfolio charts | **Recharts 3.x** | P&L over time, allocation pie chart |
| Logging | **loguru 0.7.3** | Structured logging for error tracking, job status |
| Date handling | **date-fns 4.x** (frontend), **datetime** (backend) | Ex-right dates, trade dates |

---

## New Stack Additions

### Backend: No New Libraries

**Rationale:** Every v1.1 backend feature is implementable with existing dependencies. Adding libraries for problems that are 30 lines of custom code introduces dependency risk without benefit.

#### Circuit Breaker — Custom Implementation (NOT a library)

**Decision:** Build a ~30-line `AsyncCircuitBreaker` class instead of using `aiobreaker` or `pybreaker`.

**Why not aiobreaker 1.2.0:**
- Only 3 releases ever (1.0, 1.1, 1.2) — effectively abandoned
- Internal state transitions use `threading.Lock` (not asyncio-native)
- Bug: `timeout_duration=int` crashes with `TypeError: unsupported operand type(s) for +: 'datetime.datetime' and 'int'` — requires `timedelta` (undocumented)

**Why not pybreaker 1.4.1:**
- `call_async` uses Tornado's `@gen.coroutine` — not compatible with native asyncio
- No awareness of FastAPI/asyncio patterns

**Custom implementation pattern:**
```python
class AsyncCircuitBreaker:
    """Async circuit breaker for external service calls."""
    def __init__(self, name: str, fail_max: int = 5, reset_timeout: float = 60.0):
        self.name = name
        self.fail_max = fail_max
        self.reset_timeout = reset_timeout
        self._failures = 0
        self._opened_at: float | None = None
        self._lock = asyncio.Lock()

    @property
    def is_open(self) -> bool:
        if self._opened_at is None:
            return False
        if time.monotonic() - self._opened_at >= self.reset_timeout:
            return False  # Half-open: allow one attempt
        return True

    async def call(self, func, *args, **kwargs):
        async with self._lock:
            if self.is_open:
                raise CircuitOpenError(f"{self.name} circuit is open")
        try:
            result = await func(*args, **kwargs)
            async with self._lock:
                self._failures = 0
                self._opened_at = None
            return result
        except Exception as e:
            async with self._lock:
                self._failures += 1
                if self._failures >= self.fail_max:
                    self._opened_at = time.monotonic()
            raise
```

**Where to apply:** One breaker per external service:
- `vci_breaker` — vnstock/VCI API calls
- `gemini_breaker` — Google Gemini API calls
- `cafef_breaker` — CafeF scraping calls

#### Dead-Letter Queue — DB Table Pattern

**Decision:** A `dead_letter_operations` PostgreSQL table, not a message queue.

**Why not Redis/RabbitMQ:** Single-user app, APScheduler is in-process. A DB table with `status`, `payload`, `error`, `retry_count`, `next_retry_at` is queryable, persistent, and requires zero infrastructure.

#### Job Run Tracking — DB Table Pattern

**Decision:** A `job_runs` PostgreSQL table for health monitoring.

**Why not Prometheus:** Prometheus requires a scraper + Grafana for visualization. For a personal app, a DB table queried by the existing FastAPI API + rendered by the existing Next.js dashboard is simpler and more integrated.

### Frontend: 3 New Dependencies

| Library | Version | Purpose | Why | Confidence |
|---------|---------|---------|-----|------------|
| **react-hook-form** | ~7.72 | Form state for trade entry (buy/sell) | shadcn/ui's `<Form>` component is built on top of react-hook-form. Trade entry form needs validation, error display, submit handling. Using this enables shadcn's form primitives directly. | HIGH |
| **@hookform/resolvers** | ~5.2 | Connects react-hook-form with zod | Bridge between form library and schema validation. Required for `zodResolver()`. | HIGH |
| **zod** | ~3.24 | Schema validation for forms | Validates trade entry inputs (positive quantity, valid date, price > 0). Pydantic-equivalent for TypeScript. Use zod 3.x — zod 4.x (4.3.6) is very new and `@hookform/resolvers` 5.2 is validated against zod 3.x. | HIGH |

**Why sonner/toast was considered but NOT a separate install:**
shadcn/ui 4.x's `npx shadcn@latest add sonner` handles the sonner dependency automatically. No explicit `npm install sonner` needed.

**Why numeral.js NOT recommended:**
`Intl.NumberFormat('vi-VN')` handles VND formatting natively. No library needed for `1,234,567 ₫`.

---

## Detailed Integration Points

### 1. Corporate Actions → Existing vnstock Pipeline

**Data source:** `vnstock.Vnstock().stock(symbol, source='VCI').company.events()`

**Returns DataFrame with columns (verified via source inspection):**
- `eventListCode` — Event type identifier (dividend, split, bonus, rights)
- `eventTitle` / `en_EventTitle` — Human-readable description
- `ratio` — Split/bonus ratio
- `value` — Dividend amount (VND per share) or similar
- `recordDate` → renamed to `record_date` — Record date for eligibility
- `exrightDate` → renamed to `exright_date` — Ex-rights date (when price adjusts)
- `publicDate` → renamed to `public_date`, `issueDate` → renamed to `issue_date`

**Integration:** New `CorporateActionCrawler` follows same pattern as `VnstockCrawler` — sync `Company.events()` call wrapped in `asyncio.to_thread()`. Store in `corporate_actions` table. Trigger price adjustment via job chain after crawl.

**Price adjustment formulas:**
- **Cash dividend:** `adjusted = price - dividend_per_share`
- **Stock split N:1:** `adjusted = price / N`
- **Bonus shares (ratio R):** `adjusted = price / (1 + R)`
- **Rights issue (ratio R, subscription price P):** `adjusted = (price + R × P) / (1 + R)`

Apply adjustment factors to ALL historical `adjusted_close` values before the `exrightDate`.

### 2. Portfolio P&L → Existing SQLAlchemy Models

**New models follow existing patterns in `app/models/`:**

```python
# app/models/trade.py — follows Ticker/DailyPrice model pattern
class Trade(Base):
    __tablename__ = "trades"
    id: Mapped[int]           # PK
    ticker_id: Mapped[int]    # FK → tickers.id
    trade_type: Mapped[str]   # 'buy' or 'sell'
    trade_date: Mapped[date]
    quantity: Mapped[int]
    price: Mapped[Decimal]    # Price per share (VND)
    fees: Mapped[Decimal]     # Transaction fees
    notes: Mapped[str | None]
    created_at: Mapped[datetime]
```

**FIFO cost basis:** Pure Python with `decimal.Decimal`:
```python
# On sell: dequeue oldest buy lots
remaining_sell = sell_quantity
realized_pnl = Decimal(0)
for lot in sorted(buy_lots, key=lambda l: l.trade_date):
    if remaining_sell <= 0:
        break
    deducted = min(remaining_sell, lot.remaining_quantity)
    realized_pnl += deducted * (sell_price - lot.price)
    lot.remaining_quantity -= deducted
    remaining_sell -= deducted
```

**Unrealized P&L:** `(current_close - avg_cost_basis) × remaining_shares` — current_close from latest `daily_prices` row.

### 3. AI Prompt Improvements → Existing google-genai

**What changes (no new libraries):**

1. **Use `system_instruction`** — move role/persona text from prompt body to `system_instruction` param in `GenerateContentConfig`. Already supported but currently unused.

2. **Enhanced Pydantic schemas** — add more structured fields:
```python
class TickerTechnicalAnalysis(BaseModel):
    ticker: str
    signal: TechnicalSignal
    strength: int = Field(ge=1, le=10)
    reasoning: str
    key_indicators: list[str]  # NEW: which indicators drove the signal
    risk_level: str            # NEW: low/medium/high
```

3. **Few-shot examples in prompts** — include 1-2 example outputs to improve consistency.

4. **Prompt versioning** — store prompt templates as constants with version numbers for A/B comparison.

### 4. Error Recovery → Existing tenacity + Custom Code

**Layer 1 — Retry (existing tenacity):**
Already in place on `_call_gemini()`. Extend to:
- `VnstockCrawler` methods (currently bare try/except in jobs.py)
- CafeF scraping calls

**Layer 2 — Circuit breaker (custom, see above):**
Wrap external service calls. When circuit opens, jobs fail fast instead of waiting for timeouts.

**Layer 3 — Dead-letter (DB table, see above):**
When a batch/ticker fails after all retries, insert into `dead_letter_operations` with payload. A periodic "retry dead letters" job picks up pending items.

### 5. System Health → Existing Stack + job_runs Table

**Backend:**
- New `JobRunService` writes to `job_runs` at job start/end
- New `/api/system/health` endpoint returns last crawl times, error counts, data freshness, circuit breaker states
- Existing `app/api/system.py` already has a system router — extend it

**Frontend:**
- New `/dashboard/health` page using existing shadcn Cards + Recharts + Table components
- Color-coded freshness indicators (green/yellow/red)

---

## Alternatives Considered

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| Circuit breaker | Custom ~30-line class | aiobreaker 1.2.0 | Only 3 releases, Tornado-legacy internals, `timeout_duration` bug with int |
| Circuit breaker | Custom ~30-line class | pybreaker 1.4.1 | `call_async` uses Tornado `@gen.coroutine`, not native asyncio |
| Circuit breaker | Custom ~30-line class | circuitbreaker 2.1.3 | Sync-only, no async support at all |
| Health monitoring | DB table + custom dashboard | prometheus-client 0.25 + instrumentator 7.1 | Requires Prometheus server + Grafana. Overkill for single-user |
| Health monitoring | DB table + custom dashboard | Sentry | External SaaS dependency, free tier limited |
| Dead-letter queue | PostgreSQL table | Redis Streams / RabbitMQ | Requires external infrastructure. DB table is persistent, zero-ops |
| Form validation | zod 3.24 | zod 4.3 | zod 4.x is very new, `@hookform/resolvers` tested against zod 3.x |
| Form state | react-hook-form 7.72 | Manual useState | Trade entry needs validation + shadcn Form component requires it |
| Corp action data | vnstock `Company.events()` | Direct CafeF scraping | vnstock already wraps VCI GraphQL with structured event data |
| Cost basis method | FIFO | Weighted average / LIFO | FIFO is Vietnam tax standard; simplest to implement |
| AI improvement | Prompt engineering + system_instruction | Fine-tuning / RAG | Overkill. Better prompts + structured output already available |
| Number formatting | Intl.NumberFormat | numeral.js 2.0.6 | Native browser API handles VND. Zero extra bytes |
| Toast notifications | shadcn `add sonner` | react-toastify | sonner is shadcn/ui's native toast solution |

---

## Installation

### Backend — No Changes to requirements.txt

```
# All existing deps remain as-is — NO NEW LINES NEEDED
```

### Frontend — 3 New Dependencies

```bash
cd frontend

# Form handling (for trade entry)
npm install react-hook-form @hookform/resolvers zod@3

# Add shadcn form + toast + select components (copy-paste, not npm deps)
npx shadcn@latest add form
npx shadcn@latest add sonner
npx shadcn@latest add select
npx shadcn@latest add popover
npx shadcn@latest add calendar
```

**Note:** `npx shadcn@latest add form` will auto-install `react-hook-form` and `@hookform/resolvers` as peer deps. The explicit `npm install` is for clarity.

**Note:** `zod@3` pins to latest 3.x. Do NOT use zod 4.x yet.

---

## New Database Tables Summary

| Table | Purpose | Key Columns |
|-------|---------|-------------|
| `corporate_actions` | Store split/dividend/bonus/rights events | `ticker_id`, `event_type`, `ratio`, `value`, `ex_date`, `record_date` |
| `trades` | Manual trade entries (buy/sell) | `ticker_id`, `trade_type`, `date`, `quantity`, `price`, `fees` |
| `trade_lots` | FIFO lot tracking (remaining shares per buy) | `trade_id`, `remaining_quantity` |
| `dividend_income` | Track dividend payments received | `ticker_id`, `amount`, `ex_date`, `payment_date` |
| `job_runs` | Job execution history for health monitoring | `job_name`, `status`, `started_at`, `duration`, `error` |
| `dead_letter_operations` | Failed operations for retry | `operation_type`, `payload`, `error`, `retry_count`, `status` |

All managed via Alembic migrations (already in stack).

---

## What NOT to Add

| Tempting Addition | Why Not |
|---|---|
| **Celery + Redis** for retry queue | APScheduler + DB dead-letter table is sufficient for single-user |
| **Prometheus + Grafana** for monitoring | Need separate server/dashboard. DB table + existing Next.js achieves same |
| **aiobreaker / pybreaker** for circuit breaker | No native asyncio support. Custom class is simpler |
| **zod 4.x** | Too new, `@hookform/resolvers` not yet validated against it |
| **Additional AI SDKs** (LangChain) | google-genai already does structured output, system instructions, thinking config |
| **WebSocket library** for real-time health | Polling with React Query is sufficient for personal health checks |
| **Redux Toolkit** for portfolio state | zustand (already in stack) handles client state simply |

---

## Sources & Verification

| Claim | Source | Confidence |
|-------|--------|------------|
| vnstock `Company.events()` returns corporate action data | Inspected source: `vnstock/explorer/vci/company.py` — GraphQL query includes `OrganizationEvents` with `eventListCode`, `ratio`, `value`, `exrightDate` | HIGH |
| vnstock `Company.dividends()` exists as wrapper | Inspected `vnstock/common/data.py` — delegates to `data_source.dividends()` but VCI source doesn't implement it; events() covers dividends | HIGH |
| aiobreaker uses Tornado patterns internally | Inspected source: `aiobreaker/state.py` — `call()` checks `isinstance(ret, types.GeneratorType)` | HIGH |
| aiobreaker `timeout_duration` bug | Tested: `timeout_duration=30` → `TypeError`. Requires `timedelta`. Fixed with `timedelta(seconds=30)` | HIGH |
| aiobreaker decorator works with asyncio | Tested: `@breaker async def test_func()` works, circuit opens after `fail_max` failures | HIGH |
| pybreaker `call_async` is Tornado-based | Inspected source: uses `@gen.coroutine` decorator from Tornado | HIGH |
| google-genai `system_instruction` available | Inspected `GenerateContentConfig.model_fields` — field present, accepts str/Content/parts | HIGH |
| google-genai `thinking_config` available | Already in use at `ai_analysis_service.py:422`: `ThinkingConfig(thinking_budget=1024)` | HIGH |
| tenacity 9.1.4 is installed | `pip show tenacity` → Version: 9.1.4 | HIGH |
| react-hook-form 7.72 is current | `npm view react-hook-form version` → 7.72.1 | HIGH |
| @hookform/resolvers 5.2 is current | `npm view @hookform/resolvers version` → 5.2.2 | HIGH |
| zod 3.x vs 4.x compatibility | Training data; zod 4.3.6 on npm but 3.x is mature/stable line | MEDIUM |
| FIFO is Vietnam tax standard for securities | Training data — common practice in VN brokerage systems | MEDIUM |
