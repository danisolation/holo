# Phase 1: Data Foundation - Context

**Gathered:** 2026-04-15
**Status:** Ready for planning

<domain>
## Phase Boundary

400 HOSE tickers' price and financial data flowing reliably into PostgreSQL on a daily automated schedule. This phase establishes the complete data pipeline: ticker selection, OHLCV price crawling, financial report ingestion, historical backfill, and automated daily scheduling via APScheduler. No UI, no AI analysis — pure data infrastructure.

</domain>

<decisions>
## Implementation Decisions

### Data Scope & Ticker Selection
- Top 400 HOSE tickers selected by market cap + liquidity via vnstock listing
- Ticker list refreshed weekly to catch IPOs/delistings
- Suspended/halted tickers excluded from the active 400 — they generate no price data
- Backfill 1-2 years historical data in batches of 50 tickers at a time to avoid rate limits; run once on first setup

### Crawl Schedule & Error Handling
- Daily crawl runs at 15:30 UTC+7 (45 minutes after market close) to allow VNDirect time to finalize EOD data
- 3 retries with exponential backoff (2s, 4s, 8s) using tenacity library for failed crawls
- Persistent ticker failures: log and skip, continue crawling remaining tickers. Include in daily summary.
- 2-second delay between tickers for rate limiting — conservative, ~13 min for 400 tickers

### Project Structure & Database
- Python project in `backend/` at repo root with `app/` package inside (standard FastAPI: `app/models/`, `app/services/`, `app/api/`)
- Database: yearly partitioning for daily_prices table (400 tickers × 250 days = ~100K rows/year)
- Store raw prices with adjusted_close column — both raw and adjusted preserved. Flag known corporate events.
- Configuration via pydantic-settings + .env file. Single `config.py` with Settings class. `.env.example` committed, `.env` gitignored.

### the agent's Discretion
No items deferred to agent discretion — all grey areas resolved.

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- Empty project — no existing code. This is the first implementation phase.

### Established Patterns
- Stack decisions from research: vnstock 3.5.1, FastAPI, SQLAlchemy 2.0 async, asyncpg, Alembic, APScheduler 3.11, pydantic-settings
- Async-first architecture: FastAPI + asyncpg + SQLAlchemy async engine

### Integration Points
- PostgreSQL on Aiven — connection URL via environment variable
- vnstock library wraps VNDirect/SSI APIs — primary data source
- APScheduler embeds in FastAPI process — no external broker needed

</code_context>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches within the decisions captured above.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>
