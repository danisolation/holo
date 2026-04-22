---
plan: 35-02
phase: 35-database-model-cleanup
status: complete
started: 2025-07-22
completed: 2025-07-22
---

## Summary

Removed `adjusted_close` from DailyPrice, `revenue`/`net_profit` from Financial model, and cleaned all dependent code across API, scheduler, frontend, and tests.

## What Was Built

- **Alembic migration 016**: Drops `daily_prices.adjusted_close`, `financials.revenue`, `financials.net_profit` columns
- **Model cleanup**: Removed fields from `DailyPrice` and `Financial` models
- **Service cleanup**: Removed `adjusted_close=None` from `price_service`, revenue/net_profit from `financial_service` insert/upsert
- **Deleted `corporate_action_service.py`**: Entire file removed — its sole purpose was computing adjusted_close
- **API cleanup**: Removed `adjusted_close` from `PriceResponse` schema, removed `adjusted` query parameter from prices endpoint
- **Scheduler cleanup**: Simplified `daily_corporate_action_check` — removed CorporateActionService call and Phase 3 recompute
- **Frontend cleanup**: Removed adjusted/raw toggle from CandlestickChart, simplified fetchPrices/usePrices hooks, removed adjusted state from ticker page
- **Test cleanup**: Removed 6 TestRightsIssueFactor tests, 5 TestAdjustedPriceToggle tests, 2 TestPriceResponse tests, 15 TestFactorFormulas tests, 4 TestBackwardAdjustment tests — all tested deleted CorporateActionService. Replaced with 2 simplified TestPriceEndpoint tests.

## Deviation

Plan listed 2 test files (`test_corporate_actions.py`, `test_corporate_events_api.py`) but a third file `test_corporate_actions_enhancements.py` also imported from the deleted service. Discovered during full regression run and cleaned.

## Metrics

- Tests: 689 passing (was 695 before — 32 dead tests removed, 2 replacement tests added, net -26)
- Files modified: 12
- Files deleted: 1 (corporate_action_service.py)
- LOC removed: ~537 (net)
