# Phase 14: Corporate Actions Enhancements - Context

**Gathered:** 2026-04-17
**Status:** Ready for planning

<domain>
## Phase Boundary

Extend the corporate actions system (Phase 7) with rights issue tracking, proactive ex-date Telegram alerts, a visual events calendar on the dashboard, and an adjusted/raw price toggle on candlestick charts. This phase builds on existing CorporateEvent model and CorporateEventCrawler.

</domain>

<decisions>
## Implementation Decisions

### Rights Issues Tracking
- Add `RIGHTS_ISSUE` as a new event_type in CorporateEvent model — reuse existing crawling infrastructure
- VNDirect API type code for rights: research needed but likely mapped from existing event types
- Dilution impact: compute dilution percentage from the rights ratio and display on portfolio holdings that have positions in affected tickers
- Dilution shown as an info badge/card on the holdings table — not a P&L adjustment (rights are optional, user may or may not subscribe)

### Ex-Date Telegram Alerts
- Daily scheduled job checks for events with ex_date within the next 3 business days
- Filter to watchlisted + held tickers only (not all 800 tickers)
- Alert format: "📅 Ex-date sắp tới: {symbol} — {event_type} ngày {ex_date}" with event details
- Send once per event (track sent alerts to avoid duplicates) — add `alert_sent` boolean column to CorporateEvent
- Schedule: run after daily crawl completes, before market open (e.g., 8:00 AM UTC+7)

### Events Calendar
- New dashboard page/section showing corporate events in a monthly calendar grid
- Filterable by event type (CASH_DIVIDEND, STOCK_DIVIDEND, BONUS_SHARES, RIGHTS_ISSUE, All)
- Each day cell shows event count badge, clicking expands to event list
- API endpoint: GET /api/corporate-events?month=2026-04&type=CASH_DIVIDEND
- Use a simple table-based calendar component (no external calendar library needed)

### Adjusted/Raw Price Toggle
- Existing candlestick chart uses `adjusted_close` from DailyPrice — already computed by CorporateActionService
- Add a toggle button on the chart header: "Giá điều chỉnh" (adjusted, default) / "Giá gốc" (raw)
- When toggled to raw: fetch the same price data but use `close` instead of `adjusted_close`
- Backend: add `adjusted` query param to the price history endpoint (default true)
- Frontend: toggle state stored in component local state (not global — per-chart preference)

### Agent's Discretion
- Calendar visual style (simple table grid vs fancy calendar)
- Rights issue dilution calculation formula
- Exact alert message formatting beyond the base template

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `CorporateEvent` model with event_source_id dedup, event_type, ex_date, record_date, dividend_amount, ratio, adjustment_factor
- `CorporateEventCrawler` — VNDirect REST API crawler with breaker pattern
- `CorporateActionService` — backward cumulative adjustment for adjusted_close
- `DailyPrice` model has both `close` and `adjusted_close` columns
- Telegram bot with command handler infrastructure and daily notification scheduler
- `CandlestickChart` component in frontend

### Established Patterns
- VNDirect REST API at `api-finfo.vndirect.com.vn/v4/events`
- Event types mapped via TYPE_MAP dict
- Dedup via event_source_id unique constraint
- Price adjustment uses backward cumulative factor

### Integration Points
- New event type added to `CorporateEvent.event_type` and `TYPE_MAP`
- New Telegram alert job in scheduler
- New API endpoint for calendar data
- CandlestickChart component modified for toggle

</code_context>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches. Follow existing corporate actions patterns from Phase 7.

</specifics>

<deferred>
## Deferred Ideas

- Automatic rights subscription handling (buy/sell rights) — complex portfolio implications
- Corporate event impact on AI analysis prompts — better to keep AI analysis independent

</deferred>
