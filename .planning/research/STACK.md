# Technology Stack — v2.0 Full Coverage & Real-Time

**Project:** Holo — Stock Intelligence Platform
**Milestone:** v2.0 Full Coverage & Real-Time
**Researched:** 2026-04-17
**Overall confidence:** HIGH

## Executive Summary

v2.0 needs **zero new backend Python packages** and only **3 new frontend packages**. The key finding is that the existing stack already covers every v2.0 feature with zero or minimal additions:

- **Multi-market (HNX/UPCOM)**: vnstock 3.5.1 already supports all three exchanges via VCI source. The crawler already has `_EXCHANGE_MAP = {"HOSE": "HSX", "HNX": "HNX", "UPCOM": "UPCOM"}` and the Ticker model has an `exchange` field. This is purely a logic expansion.
- **Real-time WebSocket**: FastAPI has native WebSocket support via Starlette. The `websockets` 16.0 package is already installed (dependency of `uvicorn[standard]`). vnstock supports intraday intervals (`1m`, `5m`, `15m`, `30m`) for source data polling.
- **Portfolio enhancements**: All computed from existing Trade/Lot/CorporateEvent models + new DB columns. Python stdlib `csv` handles broker CSV parsing. `python-multipart` (already installed via `fastapi[standard]`) handles file uploads.
- **Gemini usage tracking**: `google-genai` already returns `prompt_token_count`, `candidates_token_count`, `total_token_count` in `response.usage_metadata`. Just needs a new DB table + extraction logic.
- **Event calendar**: shadcn/ui's Calendar component (requires `react-day-picker` as a new frontend dep).

The deliberate restraint here is critical: **every "do we need a new library?" question answered NO for the backend.** The frontend adds `react-day-picker` (calendar via shadcn) and `papaparse` + `@types/papaparse` (CSV preview). That's it — 3 packages total.

---

## What the Existing Stack Already Covers

Before listing additions, map what v2.0 features are handled by existing packages:

| v2.0 Feature | Covered By (Existing) | How |
|---|---|---|
| HNX/UPCOM crawling | **vnstock 3.5.1** `Listing.symbols_by_exchange()` | Returns all exchanges in one call. `Quote(symbol)` works for any exchange's ticker. |
| Intraday price polling | **vnstock 3.5.1** `Quote.history(interval='1m')` | VCI supports `1m`, `5m`, `15m`, `30m`, `1H` intervals. |
| WebSocket server | **FastAPI** (Starlette) + **websockets 16.0** | `@app.websocket("/ws/prices")` — zero additional deps. |
| File upload (CSV) | **python-multipart 0.0.26** (via `fastapi[standard]`) | `UploadFile` type in FastAPI endpoints. Already installed. |
| CSV parsing (backend) | **Python stdlib `csv`** | `csv.DictReader` handles any delimiter, quoting. Zero deps. |
| Dividend income tracking | **SQLAlchemy 2.0** + existing models | Cross-reference `CorporateEvent(CASH_DIVIDEND)` with `Lot` holdings at ex_date. |
| Portfolio performance time series | **SQLAlchemy 2.0** aggregate queries | Daily portfolio value from `Lot.remaining_quantity * DailyPrice.close`. |
| Allocation pie chart data | **SQLAlchemy 2.0** aggregate queries | Group holdings by ticker/sector, compute percentages. |
| Trade edit/delete | **FastAPI** PUT/DELETE endpoints | Extend existing `PortfolioService`. FIFO lot recalculation on edit. |
| Gemini usage tracking | **google-genai 1.73** `response.usage_metadata` | Fields: `prompt_token_count`, `candidates_token_count`, `total_token_count`. |
| Pipeline timeline | Existing `job_executions` table | Already stores `started_at`, `completed_at`, `status` per job. |
| Telegram health notifications | **python-telegram-bot 22.7** | Extend existing `telegram_bot.send_message()` with health digest. |
| Rights issue tracking | Existing `CorporateEvent` model | Add `RIGHTS_ISSUE` event type. Extend VNDirect crawler. |
| Ex-date alerts | **APScheduler 3.11** + **python-telegram-bot** | New daily job checking upcoming ex-dates → send Telegram alert. |
| Adjusted/raw price toggle | Existing `adjusted_close` column in `DailyPrice` | API parameter `adjusted=true/false` → return `close` or `adjusted_close`. |
| Performance chart (frontend) | **Recharts 3.x** | Line/area chart for portfolio value over time. Already installed. |
| Allocation chart (frontend) | **Recharts 3.x** | Pie chart for holdings breakdown. Already installed. |
| Pipeline timeline (frontend) | **Recharts 3.x** | Horizontal bar chart simulating Gantt timeline. Already installed. |
| DB migrations for new tables | **Alembic 1.18** | New tables (`gemini_usage_log`, `dividend_income`, `intraday_prices`) + column additions |
| Exchange filter UI | **shadcn/ui 4.x** Select component | Dropdown for HOSE/HNX/UPCOM filter on market overview |
| Portfolio data tables | **@tanstack/react-table 8.x** | Dividend history, extended trade history with edit/delete |
| Date handling | **date-fns 4.x** (frontend), **datetime** (backend) | Ex-dates, calendar date ranges, trade dates |

---

## New Stack Additions for v2.0

### Backend: ZERO New Packages

**Rationale:** Every v2.0 backend feature is implementable with existing dependencies. The stack was designed with headroom for exactly these features.

**Verified existing capabilities used by v2.0:**

| Capability | Already Installed | Version | How Used in v2.0 |
|---|---|---|---|
| WebSocket server | `websockets` (via `uvicorn[standard]`) | 16.0 | FastAPI `@app.websocket("/ws/prices")` for real-time price push |
| File upload | `python-multipart` (via `fastapi[standard]`) | 0.0.26 | `UploadFile` type for CSV broker import endpoint |
| CSV parsing | Python stdlib `csv` | built-in | `csv.DictReader` for parsing uploaded broker CSV files |
| Intraday data | `vnstock` | 3.5.1 | `Quote.history(interval='1m')` — VCI supports 1m/5m/15m/30m/1H |
| Multi-exchange | `vnstock` | 3.5.1 | `Listing.symbols_by_exchange()` returns HSX/HNX/UPCOM tickers |
| Usage metadata | `google-genai` | 1.73.1 | `response.usage_metadata.{prompt_token_count, candidates_token_count, total_token_count}` |
| Scheduled jobs | `apscheduler` | 3.11.2 | Interval trigger for intraday polling + cron for ex-date alert check |
| Telegram messaging | `python-telegram-bot` | 22.7 | Health notifications, ex-date alerts via existing `send_message()` |

### Frontend: 3 New Dependencies

| Library | Version | Purpose | Why | Confidence |
|---------|---------|---------|-----|------------|
| **react-day-picker** | ^9.14.0 | Calendar component for event calendar view | shadcn/ui's `<Calendar>` component is built on react-day-picker. Needed for corporate event calendar showing ex-dates, dividend dates, rights issue dates. Supports date range selection, custom day rendering (event dots/badges). | HIGH |
| **papaparse** | ^5.5.3 | Client-side CSV parsing for broker import preview | Parse broker CSV files in the browser before uploading. Shows preview table of parsed trades, allows column mapping, validates data before server submission. Much better UX than blind upload. TypeScript types via `@types/papaparse`. | HIGH |
| **@types/papaparse** | ^5.5.2 | TypeScript definitions for papaparse | papaparse is plain JS. Types needed for TS project. | HIGH |

#### Previously Validated But Not Yet Installed

These were approved in v1.x research but never added as direct dependencies. v2.0 forms (trade edit, CSV column mapping) justify installing them now:

| Library | Version | Purpose | Status |
|---------|---------|---------|--------|
| **react-hook-form** | ^7.72.1 | Complex form state management | Optional. Current trade form uses plain `useState` and works fine. Only add if trade edit form or CSV mapping form becomes complex enough to justify. |
| **@hookform/resolvers** | ^5.2.2 | Zod resolver for react-hook-form | Only needed if react-hook-form is added. |

**Decision:** Do NOT pre-install react-hook-form. The existing `useState` pattern works for trade forms (proven in v1.1). Reassess during implementation — if trade edit requires complex validation or CSV column mapping needs dynamic form fields, add then. Avoid speculative dependencies.

---

## Detailed Integration Points for v2.0

### 1. Multi-Market (HNX/UPCOM) — vnstock Already Supports It

**Current code already prepared:**
```python
# vnstock_crawler.py line 23 (already exists)
_EXCHANGE_MAP = {"HOSE": "HSX", "HNX": "HNX", "UPCOM": "UPCOM"}
```

**Ticker model already has exchange field:**
```python
# models/ticker.py line 20 (already exists)
exchange: Mapped[str] = mapped_column(String(10), nullable=False, server_default="HOSE")
```

**Changes needed (all logic, no new deps):**
1. Extend `fetch_listing()` to iterate all 3 exchanges
2. Update scheduler to crawl HNX/UPCOM tickers in addition to HOSE
3. Add exchange filter to API endpoints (query parameter `?exchange=HNX`)
4. Frontend dropdown filter on market overview

**Ticker count impact:**
- HOSE: ~400 tickers (current)
- HNX: ~300+ tickers
- UPCOM: ~800+ tickers
- **Total: ~1,500+ tickers** → crawl time increases ~3-4x, need batch optimization

### 2. Real-Time WebSocket Price Streaming

**Architecture decision: FastAPI native WebSocket (NOT SSE, NOT polling-only)**

**Why WebSocket over SSE:**
- FastAPI has first-class WebSocket support via Starlette — no additional package
- `websockets` 16.0 already installed as uvicorn dependency
- Bidirectional allows clients to subscribe/unsubscribe to specific tickers
- Better for real-time price data (SSE has reconnection overhead)

**Why NOT pure react-query polling:**
- Polling at 1-minute intervals creates unnecessary HTTP overhead for many tickers
- WebSocket push is more efficient when data changes are event-driven

**Backend pattern:**
```python
# Real-time price WebSocket endpoint
@app.websocket("/ws/prices")
async def ws_prices(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            # Receive subscription message (e.g., {"subscribe": ["VNM", "FPT"]})
            data = await websocket.receive_json()
            # Handle subscription logic...
    except WebSocketDisconnect:
        pass

# Background task: poll vnstock intraday + broadcast to connected clients
class PriceBroadcaster:
    def __init__(self):
        self.connections: set[WebSocket] = set()
        self.subscriptions: dict[WebSocket, set[str]] = {}
```

**Data source for intraday:** vnstock `Quote(symbol).history(interval='1m')` via `asyncio.to_thread()` — same pattern as existing OHLCV crawl but with 1-minute interval.

**Polling frequency:** APScheduler `IntervalTrigger(minutes=1)` during market hours (9:00-11:30, 13:00-14:45 UTC+7). Outside market hours, no polling.

### 3. Portfolio Dividend Tracking

**No new packages.** Cross-reference existing data:

- `CorporateEvent` table already stores `CASH_DIVIDEND` events with `dividend_amount` and `ex_date`
- `Lot` table tracks holdings with `buy_date` and `remaining_quantity`
- **Logic:** For each CASH_DIVIDEND event, check if user held shares of that ticker at the ex_date → compute `dividend_amount × held_quantity`
- **New DB table:** `dividend_income` — caches computed dividend income per event per holding
- **API:** New `/api/portfolio/dividends` endpoint returning dividend history + totals

### 4. Trade Edit/Delete — FIFO Lot Recalculation

**No new packages.** Extend existing `PortfolioService`:

- **DELETE trade:** If BUY trade, remove associated lot. If lot partially consumed by sells, prevent deletion (or cascade). If SELL trade, reverse lot consumption.
- **EDIT trade:** Effectively DELETE old + CREATE new. Must recalculate all subsequent FIFO lot consumptions.
- **Complexity warning:** Editing old trades requires replaying all trades after the edited one to recompute lots. This is the most complex portfolio feature.

### 5. Broker CSV Import

**Backend: Python stdlib `csv` + `python-multipart` (already installed)**

```python
@router.post("/portfolio/import-csv")
async def import_csv(file: UploadFile):
    content = await file.read()
    reader = csv.DictReader(io.StringIO(content.decode("utf-8")))
    # Parse rows, map columns, validate, create trades
```

**Frontend: `papaparse` for client-side preview**

```typescript
import Papa from 'papaparse';

Papa.parse(file, {
    header: true,
    complete: (results) => {
        // Show preview table with column mapping UI
        // User maps: "Mã CK" → symbol, "Số lượng" → quantity, etc.
    }
});
```

**VN broker CSV formats (common patterns):**
- **VPS/SSI/VNDS/TCBS** typically export: Mã CK, Ngày GD, Loại (Mua/Bán), Số lượng, Giá, Phí
- Column names vary by broker → need mapping step in UI
- Date formats vary: DD/MM/YYYY (VN standard) vs YYYY-MM-DD

### 6. Gemini API Usage Tracking

**No new packages.** `google-genai` already returns usage metadata:

```python
# Already available in response object
response = await client.aio.models.generate_content(...)
usage = response.usage_metadata
# Fields:
#   usage.prompt_token_count     → int
#   usage.candidates_token_count → int
#   usage.total_token_count      → int
```

**New DB table:** `gemini_usage_log`
```
id, job_id, model, prompt_tokens, completion_tokens, total_tokens, created_at
```

**Dashboard:** Recharts area chart showing daily token usage, RPM tracking (count requests per minute from logs).

### 7. Pipeline Timeline Visualization

**No new packages.** Existing `job_executions` table already stores:
- `job_id`, `started_at`, `completed_at`, `status`

**Frontend:** Recharts `BarChart` with horizontal bars (job_id on Y-axis, time on X-axis, bar width = duration). Color-code by status (green/yellow/red). This creates a Gantt-like timeline view.

### 8. Event Calendar — react-day-picker

**New frontend dep:** `react-day-picker` ^9.14.0

**Integration with shadcn:**
```bash
npx shadcn@latest add calendar   # Installs react-day-picker as dependency
npx shadcn@latest add popover    # For date picker popovers (if not already added)
```

**Usage pattern:**
```typescript
import { Calendar } from "@/components/ui/calendar";

// Highlight dates with corporate events
<Calendar
    modifiers={{ event: eventDates }}
    modifiersClassNames={{ event: "bg-blue-100 font-bold" }}
    onDayClick={(day) => showEventsForDay(day)}
/>
```

**Data source:** Existing `/api/corporate-events` endpoint filtered by date range.

### 9. Adjusted/Raw Price Toggle

**No new packages.** Already implemented:
- `DailyPrice` model has `adjusted_close` column
- `CorporateActionService.adjust_all_tickers()` populates it

**Changes needed:**
- Add `?adjusted=true` query parameter to price endpoints
- Frontend toggle switch in chart component
- When toggled, pass different close series to lightweight-charts

---

## Alternatives Considered

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| Real-time transport | FastAPI native WebSocket | `sse-starlette` 3.3 (SSE) | WebSocket allows client to subscribe/unsubscribe to specific tickers; SSE is unidirectional |
| Real-time transport | FastAPI native WebSocket | React Query `refetchInterval` (polling) | Polling at 1-min creates N HTTP requests per interval; WebSocket push is 1 connection |
| CSV parsing (backend) | Python stdlib `csv` | `pandas.read_csv()` | stdlib csv is lighter and sufficient; no need to import pandas just for CSV parsing |
| CSV parsing (frontend) | `papaparse` 5.5 | Backend-only parsing | No client-side preview; user can't verify column mapping before upload |
| CSV parsing (frontend) | `papaparse` 5.5 | `csv-parse` (npm) | papaparse has 3x more npm downloads, better browser support, simpler API |
| Event calendar | `react-day-picker` 9.x (via shadcn) | `@fullcalendar/react` 6.1 | FullCalendar is 300KB+ with complex API. react-day-picker is ~30KB, integrates with shadcn, sufficient for month-view with event dots |
| Event calendar | `react-day-picker` 9.x | `react-big-calendar` 1.19 | Requires moment.js or date-fns adapter, heavier than needed for event dot display |
| Form management | Keep `useState` pattern | `react-hook-form` 7.72 | Existing trade form works with useState. Don't add form library speculatively — add when needed |
| Portfolio performance | Recharts line chart | `lightweight-charts` (TradingView) | lightweight-charts is for financial OHLCV data. Portfolio value is a simple time series — Recharts `<AreaChart>` is more appropriate |
| Intraday data source | vnstock `Quote.history(interval='1m')` | Direct VCI WebSocket API | VCI may have WebSocket endpoints but they're undocumented, may require auth, and vnstock doesn't wrap them. Polling vnstock is reliable and proven |
| Health notifications | Extend existing Telegram bot | Separate monitoring (Uptime Robot, etc.) | Already have Telegram infrastructure. Adding external service adds complexity |
| Gemini tracking | Custom DB table | LangSmith / Weights & Biases | External SaaS. Overkill for personal tracking. DB table + Recharts dashboard is sufficient |

---

## Installation

### Backend — No Changes to requirements.txt

```
# All existing deps remain as-is — NO NEW LINES NEEDED
# WebSocket: websockets 16.0 already installed (uvicorn[standard] dependency)
# File upload: python-multipart 0.0.26 already installed (fastapi[standard] dependency)
# CSV parsing: Python stdlib csv — no install needed
```

### Frontend — 3 New Dependencies

```bash
cd frontend

# Event calendar (react-day-picker is shadcn Calendar dependency)
npx shadcn@latest add calendar
npx shadcn@latest add popover

# CSV parsing for broker import preview
npm install papaparse @types/papaparse
```

**Note on react-day-picker:** `npx shadcn@latest add calendar` automatically installs `react-day-picker` as a dependency. No separate `npm install` needed.

**Note on zod:** Already present as transitive dependency (via shadcn). If forms need direct zod imports, add as explicit dependency: `npm install zod@3`.

**What NOT to pre-install:**
- `react-hook-form` / `@hookform/resolvers` — wait until a form is complex enough to justify
- `sonner` — add via `npx shadcn@latest add sonner` only when toast notifications are built
- No other new dependencies

---

## New Database Tables Summary

| Table | Purpose | Key Columns |
|-------|---------|-------------|
| `gemini_usage_log` | Track Gemini API token consumption per call | `job_id`, `model`, `prompt_tokens`, `completion_tokens`, `total_tokens`, `created_at` |
| `dividend_income` | Cache computed dividend income for portfolio | `ticker_id`, `corporate_event_id`, `quantity_held`, `income_amount`, `ex_date` |
| `intraday_prices` | Store latest intraday price snapshots for WebSocket broadcast | `ticker_id`, `price`, `change`, `change_pct`, `volume`, `timestamp` |

**Tables that need migration/modification:**
| Existing Table | Change | Purpose |
|---|---|---|
| `tickers` | Add index on `exchange` column | Filter queries by HNX/UPCOM/HOSE |
| `corporate_events` | Add `RIGHTS_ISSUE` to event_type values | Rights issue tracking |
| `trades` | Add `notes` column (nullable text) | Allow broker/source annotation on imported trades |
| `trades` | Add `source` column (default 'MANUAL') | Distinguish manual entry vs CSV import |

All managed via Alembic migrations (already in stack).

---

## What NOT to Add

| Tempting Addition | Why Not |
|---|---|
| **sse-starlette** for SSE streaming | FastAPI native WebSocket is already available and more capable |
| **Redis / message queue** for real-time pub/sub | Single user, single server. In-memory `set[WebSocket]` is sufficient |
| **Celery** for background tasks | APScheduler handles all scheduling. Intraday polling is just an interval trigger |
| **@fullcalendar/react** for event calendar | 300KB+ overkill. shadcn Calendar (react-day-picker) does month-view with event dots |
| **react-hook-form** (pre-install) | Current useState works. Add only when a specific form requires it |
| **D3.js** for pipeline timeline | Recharts horizontal BarChart simulates Gantt adequately |
| **Socket.IO** | Heavy abstraction over WebSocket. Native WebSocket API in browser + FastAPI is simpler |
| **polars** for data processing | vnstock outputs pandas DataFrames. Converting adds friction for no gain at ~1500 tickers |
| **External monitoring** (Sentry, DataDog) | Telegram notifications + DB-backed health dashboard covers personal use |

---

## Scaling Considerations for Multi-Market

Going from ~400 (HOSE) to ~1,500+ tickers affects:

| Concern | Current (400 tickers) | v2.0 (~1,500 tickers) | Mitigation |
|---|---|---|---|
| Daily crawl time | ~13 min | ~50+ min | Increase batch size, parallel batches per exchange |
| Intraday polling | N/A | 1,500 tickers × 1-min = too many | Only poll watched/portfolio tickers (not all 1,500) |
| DB connections | pool_size=5 | Same (queries are fast) | Monitor pool utilization on health dashboard |
| AI analysis cost | ~400 Gemini calls | ~1,500 Gemini calls | Only analyze HOSE initially; HNX/UPCOM on-demand |
| Indicator compute | ~400 tickers × 60 days | ~1,500 × 60 days | Batch compute, parallel processing |

**Key decision:** Crawl ALL tickers for price data (HNX/UPCOM), but only run AI analysis on HOSE + portfolio tickers. HNX/UPCOM AI analysis is on-demand (user requests via dashboard).

---

## Sources & Verification

| Claim | Source | Confidence |
|-------|--------|------------|
| vnstock supports HNX/UPCOM via VCI | Inspected `vnstock_crawler.py` line 23: `_EXCHANGE_MAP` already includes HNX/UPCOM; VCI `Listing.symbols_by_exchange()` returns all exchanges | HIGH |
| vnstock supports intraday intervals | Inspected `vnstock/explorer/vci/const.py`: `_INTERVAL_MAP = {'1m': 'ONE_MINUTE', '5m': 'ONE_MINUTE', '15m': 'ONE_MINUTE', ...}` | HIGH |
| FastAPI has native WebSocket support | Tested: `from starlette.websockets import WebSocket` — available. Starlette 1.0.0 installed | HIGH |
| websockets 16.0 is installed | `importlib.metadata.version('websockets')` → 16.0. Dependency of `uvicorn[standard]` | HIGH |
| python-multipart 0.0.26 is installed | `importlib.metadata.version('python-multipart')` → 0.0.26. Dependency of `fastapi[standard]` | HIGH |
| google-genai returns usage_metadata | Inspected `types.GenerateContentResponseUsageMetadata` — fields: `prompt_token_count`, `candidates_token_count`, `total_token_count` (+ 8 more) | HIGH |
| Ticker model has exchange field | Inspected `app/models/ticker.py` line 20: `exchange: Mapped[str] = mapped_column(String(10), ..., server_default="HOSE")` | HIGH |
| DailyPrice has adjusted_close | CorporateActionService already computes and stores `adjusted_close` | HIGH |
| react-day-picker 9.14.0 is current | `npm view react-day-picker version` → 9.14.0 | HIGH |
| papaparse 5.5.3 is current | `npm view papaparse version` → 5.5.3 | HIGH |
| @types/papaparse 5.5.2 is current | `npm view @types/papaparse version` → 5.5.2 | HIGH |
| react-hook-form 7.72.1 is current | `npm view react-hook-form version` → 7.72.1 | HIGH |
| @hookform/resolvers 5.2.2 is current | `npm view @hookform/resolvers version` → 5.2.2 | HIGH |
| shadcn Calendar uses react-day-picker | shadcn docs; Calendar component source wraps react-day-picker | HIGH |
| @fullcalendar/react size ~300KB | Training data — FullCalendar is a heavy library | MEDIUM |
