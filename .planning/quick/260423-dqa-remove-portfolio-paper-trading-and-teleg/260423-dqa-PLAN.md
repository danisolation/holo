---
phase: quick
plan: 260423-dqa
type: execute
wave: 1
depends_on: []
files_modified:
  # Backend DELETE
  - backend/app/api/portfolio.py
  - backend/app/services/portfolio_service.py
  - backend/app/services/csv_import_service.py
  - backend/app/schemas/portfolio.py
  - backend/app/models/trade.py
  - backend/app/models/lot.py
  - backend/tests/test_portfolio.py
  - backend/tests/test_csv_import.py
  - backend/app/api/paper_trading.py
  - backend/app/services/paper_trade_service.py
  - backend/app/services/paper_trade_analytics_service.py
  - backend/app/schemas/paper_trading.py
  - backend/app/models/paper_trade.py
  - backend/app/models/simulation_config.py
  - backend/app/services/analytics_base.py
  - backend/app/schemas/trade.py
  - backend/tests/test_paper_trade_api.py
  - backend/tests/test_paper_trade_analytics.py
  - backend/tests/test_paper_trade_auto_track.py
  - backend/tests/test_paper_trade_model.py
  - backend/tests/test_paper_trade_pnl.py
  - backend/tests/test_paper_trade_state_machine.py
  - backend/tests/test_position_monitor.py
  - backend/tests/test_position_sizing.py
  - backend/tests/test_analytics_base.py
  - backend/app/telegram/bot.py
  - backend/app/telegram/handlers.py
  - backend/app/telegram/formatter.py
  - backend/app/telegram/services.py
  - backend/app/telegram/__init__.py
  - backend/app/services/exdate_alert_service.py
  - backend/app/services/health_alert_service.py
  - backend/tests/test_telegram.py
  - backend/tests/test_exdate_alerts.py
  - backend/tests/test_health_alerts.py
  # Backend EDIT
  - backend/app/api/router.py
  - backend/app/models/__init__.py
  - backend/app/main.py
  - backend/app/scheduler/manager.py
  - backend/app/scheduler/jobs.py
  - backend/tests/test_resilience.py
  - backend/tests/test_scheduler.py
  # Backend CREATE
  - backend/alembic/versions/018_drop_portfolio_paper_trading_tables.py
  # Frontend DELETE
  - frontend/src/app/dashboard/portfolio/
  - frontend/src/app/dashboard/paper-trading/
  - frontend/src/components/portfolio-summary.tsx
  - frontend/src/components/holdings-table.tsx
  - frontend/src/components/allocation-chart.tsx
  - frontend/src/components/performance-chart.tsx
  - frontend/src/components/trade-form.tsx
  - frontend/src/components/trade-edit-dialog.tsx
  - frontend/src/components/trade-delete-confirm.tsx
  - frontend/src/components/trade-history.tsx
  - frontend/src/components/csv-import-dialog.tsx
  - frontend/src/components/csv-preview-table.tsx
  - frontend/src/components/paper-trading/
  - frontend/src/components/shared/generic-trades-table.tsx
  - frontend/src/components/shared/equity-curve-chart.tsx
  - frontend/e2e/api-paper-trading.spec.ts
  - frontend/e2e/flow-paper-trading-dashboard.spec.ts
  - frontend/e2e/flow-settings.spec.ts
  - frontend/e2e/flow-ticker-to-trade.spec.ts
  - frontend/e2e/interact-pt-settings.spec.ts
  - frontend/e2e/interact-pt-tabs.spec.ts
  - frontend/e2e/interact-trades-table.spec.ts
  # Frontend EDIT
  - frontend/src/lib/api.ts
  - frontend/src/lib/hooks.ts
  - frontend/src/components/navbar.tsx
  - frontend/e2e/api-smoke.spec.ts
  - frontend/e2e/page-smoke.spec.ts
  - frontend/e2e/navigation.spec.ts
  - frontend/e2e/visual-pages.spec.ts
  - frontend/e2e/visual-charts.spec.ts
  - frontend/e2e/visual-responsive.spec.ts
  - frontend/e2e/api-errors.spec.ts
  - frontend/e2e/fixtures/test-helpers.ts
  - frontend/e2e/fixtures/api-helpers.ts
autonomous: true
must_haves:
  truths:
    - "Portfolio, Paper Trading, and Telegram Bot features are completely removed from codebase"
    - "Backend starts without import errors (no references to deleted modules)"
    - "Frontend compiles without TypeScript errors"
    - "All remaining backend tests pass"
    - "Alembic migration drops the 4 tables cleanly"
  artifacts:
    - path: "backend/alembic/versions/018_drop_portfolio_paper_trading_tables.py"
      provides: "Migration to drop paper_trades, simulation_config, lots, trades tables + enums"
  key_links:
    - from: "backend/app/api/router.py"
      to: "backend/app/api/*.py"
      via: "router imports"
      pattern: "No portfolio_router or paper_trading_router imports"
    - from: "backend/app/main.py"
      to: "backend/app/telegram/"
      via: "telegram_bot import removed"
      pattern: "No telegram imports in main.py"
    - from: "frontend/src/lib/hooks.ts"
      to: "frontend/src/lib/api.ts"
      via: "imports"
      pattern: "No portfolio or paper trading imports"
---

<objective>
Remove Portfolio, Paper Trading, and Telegram Bot features entirely from the codebase.

Purpose: v7.0 consolidation — these features are no longer needed. Backtest was already removed in quick task 260423-d83.
Output: Clean codebase with only core features (tickers, analysis, watchlist, health, corporate events, trading signals).
</objective>

<execution_context>
@~/.copilot/get-shit-done/workflows/execute-plan.md
@~/.copilot/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@CLAUDE.md
</context>

<tasks>

<task type="auto">
  <name>Task 1: Backend — Delete files, edit shared modules, create migration</name>
  <files>
    backend/app/api/portfolio.py, backend/app/services/portfolio_service.py, backend/app/services/csv_import_service.py, backend/app/schemas/portfolio.py, backend/app/models/trade.py, backend/app/models/lot.py, backend/tests/test_portfolio.py, backend/tests/test_csv_import.py,
    backend/app/api/paper_trading.py, backend/app/services/paper_trade_service.py, backend/app/services/paper_trade_analytics_service.py, backend/app/schemas/paper_trading.py, backend/app/models/paper_trade.py, backend/app/models/simulation_config.py, backend/app/services/analytics_base.py, backend/app/schemas/trade.py, backend/tests/test_paper_trade_api.py, backend/tests/test_paper_trade_analytics.py, backend/tests/test_paper_trade_auto_track.py, backend/tests/test_paper_trade_model.py, backend/tests/test_paper_trade_pnl.py, backend/tests/test_paper_trade_state_machine.py, backend/tests/test_position_monitor.py, backend/tests/test_position_sizing.py, backend/tests/test_analytics_base.py,
    backend/app/telegram/ (entire directory), backend/app/services/exdate_alert_service.py, backend/app/services/health_alert_service.py, backend/tests/test_telegram.py, backend/tests/test_exdate_alerts.py, backend/tests/test_health_alerts.py,
    backend/app/api/router.py, backend/app/models/__init__.py, backend/app/main.py, backend/app/scheduler/manager.py, backend/app/scheduler/jobs.py, backend/tests/test_resilience.py, backend/tests/test_scheduler.py,
    backend/alembic/versions/018_drop_portfolio_paper_trading_tables.py
  </files>
  <action>
**Step 1: Delete all portfolio backend files (8 files):**
```
Remove-Item backend/app/api/portfolio.py
Remove-Item backend/app/services/portfolio_service.py
Remove-Item backend/app/services/csv_import_service.py
Remove-Item backend/app/schemas/portfolio.py
Remove-Item backend/app/models/trade.py
Remove-Item backend/app/models/lot.py
Remove-Item backend/tests/test_portfolio.py
Remove-Item backend/tests/test_csv_import.py
```

**Step 2: Delete all paper trading backend files (15 files):**
```
Remove-Item backend/app/api/paper_trading.py
Remove-Item backend/app/services/paper_trade_service.py
Remove-Item backend/app/services/paper_trade_analytics_service.py
Remove-Item backend/app/schemas/paper_trading.py
Remove-Item backend/app/models/paper_trade.py
Remove-Item backend/app/models/simulation_config.py
Remove-Item backend/app/services/analytics_base.py
Remove-Item backend/app/schemas/trade.py
Remove-Item backend/tests/test_paper_trade_api.py
Remove-Item backend/tests/test_paper_trade_analytics.py
Remove-Item backend/tests/test_paper_trade_auto_track.py
Remove-Item backend/tests/test_paper_trade_model.py
Remove-Item backend/tests/test_paper_trade_pnl.py
Remove-Item backend/tests/test_paper_trade_state_machine.py
Remove-Item backend/tests/test_position_monitor.py
Remove-Item backend/tests/test_position_sizing.py
Remove-Item backend/tests/test_analytics_base.py
```

**Step 3: Delete entire telegram directory + alert services (6 files):**
```
Remove-Item -Recurse backend/app/telegram/
Remove-Item backend/app/services/exdate_alert_service.py
Remove-Item backend/app/services/health_alert_service.py
Remove-Item backend/tests/test_telegram.py
Remove-Item backend/tests/test_exdate_alerts.py
Remove-Item backend/tests/test_health_alerts.py
```

**Step 4: Edit `backend/app/api/router.py`:**
Remove lines 7, 10 (portfolio/paper_trading imports) and lines 16, 19 (include_router calls). Final file should be:
```python
"""Main API router combining all sub-routers."""
from fastapi import APIRouter

from app.api.system import router as system_router
from app.api.analysis import router as analysis_router
from app.api.tickers import router as tickers_router
from app.api.health import router as health_router
from app.api.corporate_events import router as corporate_events_router

api_router = APIRouter()
api_router.include_router(system_router)
api_router.include_router(analysis_router)
api_router.include_router(tickers_router)
api_router.include_router(health_router)
api_router.include_router(corporate_events_router)
```

**Step 5: Edit `backend/app/models/__init__.py`:**
Remove lines 19-20 (Trade, Lot imports), line 22-23 (PaperTrade, SimulationConfig imports). Update `__all__` to remove Trade, Lot, PaperTrade, TradeStatus, TradeDirection, SimulationConfig. Final file:
```python
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


# Import all models so Alembic can detect them
from app.models.ticker import Ticker  # noqa: E402
from app.models.daily_price import DailyPrice  # noqa: E402
from app.models.financial import Financial  # noqa: E402
from app.models.technical_indicator import TechnicalIndicator  # noqa: E402
from app.models.ai_analysis import AIAnalysis, AnalysisType  # noqa: E402
from app.models.news_article import NewsArticle  # noqa: E402
from app.models.user_watchlist import UserWatchlist  # noqa: E402
from app.models.job_execution import JobExecution  # noqa: E402
from app.models.failed_job import FailedJob  # noqa: E402
from app.models.corporate_event import CorporateEvent  # noqa: E402
from app.models.gemini_usage import GeminiUsage  # noqa: E402

__all__ = ["Base", "Ticker", "DailyPrice", "Financial", "TechnicalIndicator", "AIAnalysis", "AnalysisType", "NewsArticle", "UserWatchlist", "JobExecution", "FailedJob", "CorporateEvent", "GeminiUsage"]
```

**Step 6: Edit `backend/app/main.py`:**
- Remove line 17: `from app.telegram.bot import telegram_bot`
- Line 27: Change message to `"HOLO_TEST_MODE=true — skipping scheduler"`
- Remove lines 32-35 (telegram_bot.start block)
- Remove lines 38-42 (telegram_bot.stop block in shutdown)
Final lifespan:
```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle: start scheduler on startup, clean up on shutdown."""
    # Startup
    logger.info("Holo starting up...")
    if settings.holo_test_mode:
        logger.info("HOLO_TEST_MODE=true — skipping scheduler")
    else:
        configure_jobs()
        scheduler.start()
        logger.info("Scheduler started with configured jobs")
    yield
    # Shutdown
    if not settings.holo_test_mode:
        scheduler.shutdown(wait=False)
        logger.info("Scheduler shut down")
    await engine.dispose()
    logger.info("Database engine disposed. Holo shut down.")
```

**Step 7: Edit `backend/app/scheduler/manager.py`:**

7a. Remove line 15: `from app.telegram.formatter import MessageFormatter`

7b. Remove from `_JOB_NAMES` dict these entries:
- `"daily_signal_alert_check_triggered"` 
- `"daily_exdate_alert_check_triggered"`
- `"daily_summary_send"`
- `"health_alert_check"`
- `"paper_trade_auto_track_triggered"`
- `"paper_position_monitor_triggered"`

7c. Replace the entire `_on_job_error` function (lines 54-75) with a log-only version:
```python
def _on_job_error(event: events.JobExecutionEvent):
    """Log complete job failure (formerly sent Telegram notification)."""
    job_name = _JOB_NAMES.get(event.job_id, event.job_id.replace("_", " ").title())
    error_msg = str(event.exception)[:200] if event.exception else "Unknown error"
    logger.error(f"CRITICAL FAILURE ALERT: {job_name} — {error_msg}")
```

7d. In `_on_job_executed` function:
- Remove the block at lines 106-114 that chains `paper_position_monitor` after `daily_price_crawl_upcom`.
- Remove the block at lines 115-124 that chains `daily_exdate_alert_check` after `daily_corporate_action_check_triggered`. Also remove the entire `elif event.job_id == "daily_corporate_action_check_triggered":` branch since the only thing it did was chain exdate alerts.
- Remove the block at lines 190-198 that chains `paper_trade_auto_track` after `daily_trading_signal_triggered`.
- In the `daily_trading_signal_triggered` branch (lines 171-198), also remove the `daily_signal_alert_check` chain (lines 172-180) — since signal alerts used telegram. Keep only the `daily_hnx_upcom_analysis` chain.

The final elif for `daily_trading_signal_triggered` should be:
```python
    elif event.job_id in ("daily_trading_signal_triggered",):
        # Chain HNX/UPCOM watchlist analysis
        from app.scheduler.jobs import daily_hnx_upcom_analysis
        logger.info("Chaining: daily_trading_signal → daily_hnx_upcom_analysis")
        scheduler.add_job(
            daily_hnx_upcom_analysis,
            id="daily_hnx_upcom_analysis_triggered",
            replace_existing=True,
            misfire_grace_time=3600,
        )
```

7e. In `configure_jobs()`:
- Remove lines 265-280 (daily_summary_send job registration).
- Remove lines 282-295 (health_alert_check job registration).
- Update the logger.info at line 297 to remove `daily_summary_send` and `health_alert_check` references. New log:
```python
    logger.info(
        f"Scheduled jobs: daily_price_crawl_hose (Mon-Fri 15:30 {settings.timezone}), "
        f"daily_price_crawl_hnx (Mon-Fri 16:00), daily_price_crawl_upcom (Mon-Fri 16:30), "
        f"weekly_ticker_refresh (Sun 10:00), weekly_financial_crawl (Sat 08:00)"
    )
```
- Update the chaining log at lines 335-338 to remove exdate_alert_check and paper references:
```python
    logger.info(
        "Job chaining registered: "
        "daily_price_crawl_upcom → [indicators → AI → news → sentiment → combined → trading_signal → hnx_upcom_analysis] + [corporate_action_check]"
    )
```

**Step 8: Edit `backend/app/scheduler/jobs.py`:**
Delete these 6 functions entirely (keep everything else intact):
- `daily_signal_alert_check()` (lines 485-511)
- `daily_summary_send()` (lines 514-540)
- `daily_exdate_alert_check()` (lines 593-619)
- `health_alert_check()` (lines 650-666)
- `paper_trade_auto_track()` (lines 714-838)
- `paper_position_monitor()` (lines 841-998)

Keep these functions: `daily_price_crawl_for_exchange`, `weekly_ticker_refresh`, `weekly_financial_crawl`, `daily_indicator_compute`, `daily_ai_analysis`, `daily_news_crawl`, `daily_sentiment_analysis`, `daily_combined_analysis`, `daily_trading_signal_analysis`, `daily_corporate_action_check`, `daily_hnx_upcom_analysis`, `realtime_price_poll`, `realtime_heartbeat`.

**Step 9: Edit `backend/tests/test_resilience.py`:**
Delete the entire `TestTelegramNotification` class (lines 292-317) and `TestAlertJobsNeverRaise` class (lines 320-348). These test telegram notification and signal_alert_check which are both removed.

**Step 10: Edit `backend/tests/test_scheduler.py`:**
- In `test_configure_jobs_registers_six_jobs` (line 24): Remove assertions for `daily_summary_send` (line 39) and `health_alert_check` (line 40). Update `len(job_ids) == 9` to `len(job_ids) == 7` (3 exchange crawls + weekly ticker + weekly financial + realtime poll + realtime heartbeat). Update the docstring to reflect the new count.
- In the test around line 223: Remove assertion for `daily_summary_send`.

**Step 11: Create Alembic migration `backend/alembic/versions/018_drop_portfolio_paper_trading_tables.py`:**
```python
"""Drop portfolio and paper trading tables.

Portfolio (trades, lots) and Paper Trading (paper_trades, simulation_config)
features removed in v7.0 consolidation.
DO NOT delete migration 007 or 013 — they are part of the migration chain.

Revision ID: 018
Revises: 017
Create Date: 2025-07-23
"""
from typing import Sequence, Union
from alembic import op

revision: str = "018"
down_revision: Union[str, None] = "017"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop tables (order: children first due to FK constraints)
    op.drop_table("lots")           # FK → trades
    op.drop_table("trades")         # FK → tickers
    op.drop_table("paper_trades")   # FK → tickers, ai_analyses
    op.drop_table("simulation_config")

    # Drop enums (only used by paper_trades — safe to drop)
    op.execute("DROP TYPE IF EXISTS trade_status")
    op.execute("DROP TYPE IF EXISTS trade_direction")


def downgrade() -> None:
    # Not implementing downgrade — these features are permanently removed
    raise NotImplementedError("Cannot downgrade: portfolio and paper trading features permanently removed")
```
  </action>
  <verify>
    <automated>cd backend && python -c "from app.api.router import api_router; print(f'Routes: {len(api_router.routes)}')" && python -c "from app.models import Base; print(f'Models OK: {len(Base.metadata.tables)} tables')" && python -c "from app.main import app; print('App import OK')" && python -c "from app.scheduler.manager import configure_jobs; print('Scheduler import OK')"</automated>
  </verify>
  <done>All portfolio, paper trading, and telegram backend files deleted. Shared modules (router, models/__init__, main, scheduler/manager, scheduler/jobs) cleaned of all references. Alembic migration 018 created. Backend imports succeed without errors.</done>
</task>

<task type="auto">
  <name>Task 2: Frontend — Delete files, clean api/hooks/navbar, clean E2E tests</name>
  <files>
    frontend/src/app/dashboard/portfolio/, frontend/src/app/dashboard/paper-trading/,
    frontend/src/components/portfolio-summary.tsx, frontend/src/components/holdings-table.tsx, frontend/src/components/allocation-chart.tsx, frontend/src/components/performance-chart.tsx, frontend/src/components/trade-form.tsx, frontend/src/components/trade-edit-dialog.tsx, frontend/src/components/trade-delete-confirm.tsx, frontend/src/components/trade-history.tsx, frontend/src/components/csv-import-dialog.tsx, frontend/src/components/csv-preview-table.tsx,
    frontend/src/components/paper-trading/, frontend/src/components/shared/generic-trades-table.tsx, frontend/src/components/shared/equity-curve-chart.tsx,
    frontend/e2e/api-paper-trading.spec.ts, frontend/e2e/flow-paper-trading-dashboard.spec.ts, frontend/e2e/flow-settings.spec.ts, frontend/e2e/flow-ticker-to-trade.spec.ts, frontend/e2e/interact-pt-settings.spec.ts, frontend/e2e/interact-pt-tabs.spec.ts, frontend/e2e/interact-trades-table.spec.ts,
    frontend/src/lib/api.ts, frontend/src/lib/hooks.ts, frontend/src/components/navbar.tsx,
    frontend/e2e/api-smoke.spec.ts, frontend/e2e/page-smoke.spec.ts, frontend/e2e/navigation.spec.ts, frontend/e2e/visual-pages.spec.ts, frontend/e2e/visual-charts.spec.ts, frontend/e2e/visual-responsive.spec.ts, frontend/e2e/api-errors.spec.ts, frontend/e2e/fixtures/test-helpers.ts, frontend/e2e/fixtures/api-helpers.ts
  </files>
  <action>
**Step 1: Delete frontend page directories:**
```
Remove-Item -Recurse frontend/src/app/dashboard/portfolio/
Remove-Item -Recurse frontend/src/app/dashboard/paper-trading/
```

**Step 2: Delete portfolio component files (10 files):**
```
Remove-Item frontend/src/components/portfolio-summary.tsx
Remove-Item frontend/src/components/holdings-table.tsx
Remove-Item frontend/src/components/allocation-chart.tsx
Remove-Item frontend/src/components/performance-chart.tsx
Remove-Item frontend/src/components/trade-form.tsx
Remove-Item frontend/src/components/trade-edit-dialog.tsx
Remove-Item frontend/src/components/trade-delete-confirm.tsx
Remove-Item frontend/src/components/trade-history.tsx
Remove-Item frontend/src/components/csv-import-dialog.tsx
Remove-Item frontend/src/components/csv-preview-table.tsx
```

**Step 3: Delete paper trading component directory + shared components with no consumers:**
```
Remove-Item -Recurse frontend/src/components/paper-trading/
Remove-Item frontend/src/components/shared/generic-trades-table.tsx
Remove-Item frontend/src/components/shared/equity-curve-chart.tsx
```
Check if `frontend/src/components/shared/` is now empty — if so, remove the directory too.

**Step 4: Delete E2E test files (7 files):**
```
Remove-Item frontend/e2e/api-paper-trading.spec.ts
Remove-Item frontend/e2e/flow-paper-trading-dashboard.spec.ts
Remove-Item frontend/e2e/flow-settings.spec.ts
Remove-Item frontend/e2e/flow-ticker-to-trade.spec.ts
Remove-Item frontend/e2e/interact-pt-settings.spec.ts
Remove-Item frontend/e2e/interact-pt-tabs.spec.ts
Remove-Item frontend/e2e/interact-trades-table.spec.ts
```

**Step 5: Edit `frontend/src/lib/api.ts`:**
- Delete everything from line 207 (`// --- Portfolio Types ---`) through line 393 (end of `importCSV` function, just before `// --- Health Types ---`). This removes all portfolio types and fetch functions.
- Delete everything from line 582 (`// --- Paper Trading Types (Phase 25) ---`) through line 839 (end of file). This removes all paper trading types and fetch functions.
- Keep: lines 1-205 (Ticker/Analysis types+fetchers) and lines 394-581 (Health/GeminiUsage/PipelineTimeline types+fetchers).

**Step 6: Edit `frontend/src/lib/hooks.ts`:**
- Remove all portfolio and paper trading imports from the import block (lines 12-52). Keep only: `fetchTickers, fetchPrices, fetchIndicators, fetchAnalysisSummary, fetchTradingSignal, fetchMarketOverview, triggerOnDemandAnalysis, fetchJobStatuses, fetchDataFreshness, fetchErrorRates, fetchDbPool, fetchHealthSummary, triggerJob, fetchCorporateEvents, fetchGeminiUsage, fetchPipelineTimeline`.
- Delete everything from line 132 (`// --- Portfolio Hooks ---`) through line 339 (end of `useTradingSignal`). Wait — useTradingSignal should be KEPT (lines 330-339). So delete lines 132-328 (all portfolio hooks), keep lines 330-339 (useTradingSignal).
- Delete everything from line 341 (`// --- Paper Trading Hooks (Phase 25) ---`) through line 495 (end of file).

**Step 7: Edit `frontend/src/components/navbar.tsx`:**
Remove these two entries from the `NAV_LINKS` array:
- `{ href: "/dashboard/portfolio", label: "Đầu tư" },`
- `{ href: "/dashboard/paper-trading", label: "Paper Trading" },`

Final NAV_LINKS:
```typescript
const NAV_LINKS = [
  { href: "/", label: "Tổng quan" },
  { href: "/watchlist", label: "Danh mục" },
  { href: "/dashboard", label: "Bảng điều khiển" },
  { href: "/dashboard/corporate-events", label: "Sự kiện" },
  { href: "/dashboard/health", label: "Hệ thống" },
];
```

**Step 8: Edit E2E test files:**

8a. `frontend/e2e/api-smoke.spec.ts`: Delete the entire `test.describe('API Smoke Tests — Portfolio', ...)` block (lines 163-202). Keep all other smoke tests.

8b. `frontend/e2e/page-smoke.spec.ts`:
- Remove `Paper Trading renders tabs` test (lines 28-32).
- Remove `Portfolio page renders content` test (lines 56-60).
- Keep all other tests.

8c. `frontend/e2e/navigation.spec.ts`:
- In `test('Navbar links navigate to correct pages')`: Remove the Paper Trading click+URL assertion block (lines 17-19). Keep Watchlist, Dashboard, and Home navigation.
- In `test('Navbar is visible on all pages')`: Remove `/dashboard/paper-trading` from the routes array (line 27). New array: `['/', '/watchlist', '/dashboard', '/dashboard/health']`.

8d. `frontend/e2e/visual-pages.spec.ts`:
- Remove the `VIS-01: Paper Trading page baseline` test (lines 60-69).
- Remove the `VIS-01: Portfolio page baseline` test (lines 71-79).

8e. `frontend/e2e/visual-charts.spec.ts`:
- Remove the `VIS-02: Recharts SVG charts exist in analytics tab` test (lines 58-92) — it navigates to paper-trading.
- Remove the `VIS-02: Analytics tab screenshot baseline` test (lines 94-115) — it navigates to paper-trading.
- Keep the two candlestick chart tests (lines 17-56) — they test ticker detail which is retained.

8f. `frontend/e2e/visual-responsive.spec.ts`:
- Remove `VIS-04: Paper Trading renders at mobile viewport` test (lines 56-77).
- Remove `VIS-04: Portfolio renders at mobile viewport` test (lines 126-144).

8g. `frontend/e2e/api-errors.spec.ts`:
- Remove `Non-existent paper trade ID returns 404` test (lines 34-37).
- Remove `Invalid PUT config body returns 422` test (lines 46-53) — tests paper-trading config.
- Remove `Invalid trades direction filter returns 422` test (lines 60-63) — tests paper-trading trades.

8h. `frontend/e2e/fixtures/test-helpers.ts`:
- Remove `{ path: '/dashboard/paper-trading', name: 'Paper Trading' },` from APP_ROUTES.
- Remove `{ path: '/dashboard/portfolio', name: 'Portfolio' },` from APP_ROUTES.

8i. `frontend/e2e/fixtures/api-helpers.ts`:
- Remove `getPaperSettings()`, `getPaperTrades()`, and `getPaperAnalytics()` methods from the ApiHelpers class (lines 33-48).
  </action>
  <verify>
    <automated>cd frontend && npx tsc --noEmit 2>&1 | Select-Object -First 20</automated>
  </verify>
  <done>All portfolio, paper trading frontend files deleted. api.ts, hooks.ts, navbar.tsx cleaned. All E2E test files cleaned of portfolio/paper-trading/telegram references. TypeScript compiles without errors.</done>
</task>

<task type="auto">
  <name>Task 3: Full verification — backend tests + frontend build</name>
  <files>None (verification only)</files>
  <action>
**Step 1: Run backend tests (excluding deleted test files):**
```bash
cd backend && python -m pytest tests/ -x --timeout=30 -q 2>&1 | tail -20
```
If any test fails due to leftover references to portfolio/paper_trading/telegram, fix those references.

**Step 2: Verify frontend builds:**
```bash
cd frontend && npm run build 2>&1 | tail -20
```
If build fails, check for leftover imports to deleted components.

**Step 3: Grep for leftover references — confirm zero hits:**
```bash
# Backend: grep for dead imports
grep -rn "paper_trad\|portfolio\|telegram" backend/app/ --include="*.py" | grep -v "__pycache__" | grep -v "alembic"
# Should return ZERO lines (only alembic migration files can mention these)

# Frontend: grep for dead imports
grep -rn "paper-trading\|portfolio\|telegram" frontend/src/ --include="*.ts" --include="*.tsx" | grep -v "node_modules"
# Should return ZERO lines
```
Fix any leftover references found.

**Step 4: Verify no snapshot directories need cleanup:**
Check if `frontend/e2e/visual-pages.spec.ts-snapshots/` has paper-trading or portfolio screenshot files — delete them if found (they're stale baselines).
Check `frontend/e2e/visual-responsive.spec.ts-snapshots/` similarly.

**Step 5: Commit everything atomically:**
```bash
git add -A && git commit -m "feat(v7): remove portfolio, paper trading, and telegram bot features

- Delete all portfolio backend (api, service, schema, model, tests)
- Delete all paper trading backend (api, services, schemas, models, tests)
- Delete entire telegram directory + alert services
- Clean scheduler: remove 6 deleted jobs, telegram notification, dead chains
- Clean main.py: remove telegram bot lifecycle
- Clean router.py, models/__init__.py
- Delete all portfolio frontend (page, 10 components, hooks, api types)
- Delete all paper trading frontend (page, 11+ components, shared components)
- Clean navbar, api.ts, hooks.ts
- Clean 10+ E2E test files (remove dead tests, fixtures, visual snapshots)
- Add Alembic migration 018: drop trades, lots, paper_trades, simulation_config tables
- Drop trade_status, trade_direction enums"
```
  </action>
  <verify>
    <automated>cd backend && python -m pytest tests/ -x --timeout=30 -q 2>&1 | Select-Object -Last 5</automated>
  </verify>
  <done>All backend tests pass. Frontend builds successfully. Zero leftover references to portfolio, paper trading, or telegram in app code. Migration 018 ready to run. Single atomic commit.</done>
</task>

</tasks>

<verification>
1. `python -c "from app.main import app"` — no import errors
2. `python -m pytest tests/ -x -q` — all remaining tests pass
3. `npx tsc --noEmit` — zero TypeScript errors
4. `npm run build` — frontend builds clean
5. `grep -rn "paper_trad\|portfolio\|telegram" backend/app/ --include="*.py" | grep -v __pycache__ | grep -v alembic` — zero hits
6. `grep -rn "paper-trading\|portfolio" frontend/src/ --include="*.ts" --include="*.tsx"` — zero hits
</verification>

<success_criteria>
- All 3 features (Portfolio, Paper Trading, Telegram Bot) completely removed
- Zero import errors in backend
- Zero TypeScript errors in frontend
- All remaining backend tests pass
- Frontend builds successfully
- Alembic migration 018 drops 4 tables + 2 enums
- Single atomic git commit
</success_criteria>

<output>
After completion, create `.planning/quick/260423-dqa-remove-portfolio-paper-trading-and-teleg/260423-dqa-SUMMARY.md`
</output>
