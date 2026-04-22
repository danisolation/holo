---
plan: 35-01
phase: 35-database-model-cleanup
status: complete
started: 2025-07-22
completed: 2025-07-22
---

## Summary

Removed the dead `price_alerts` feature and the unused `news_article.source` column from the entire codebase.

## What Was Built

- **Alembic migration 015**: Drops `price_alerts` table and `news_articles.source` column with proper downgrade
- **Model cleanup**: Deleted `price_alert.py`, removed `source` field from `NewsArticle`
- **Handler cleanup**: Removed `/alert` command handler, `alert_command` function, `PriceAlert` import
- **Service cleanup**: Removed `check_price_alerts()` method from `AlertService`
- **Scheduler cleanup**: Removed `daily_price_alert_check` job and its chaining from `manager.py`
- **Crawler cleanup**: Removed `"source": "cafef"` from `cafef_crawler` article parsing and insertion
- **Formatter cleanup**: Removed `alert_created()`, `alert_triggered()` methods and `/alert` from welcome
- **Test cleanup**: Removed 6 alert-related tests, updated handler count (11→10), chain count (4→3)

## Key Decisions

- Kept `Decimal` import in handlers.py (still used by other functions)
- Kept `String` import in news_article.py (still used by `url` field)

## Deviations

- Plan missed several test assertions referencing alert features (welcome command test, handler registration count test, formatter alert methods tests). Fixed during execution.

## Test Results

76 tests passing across `test_telegram.py`, `test_scheduler.py`, `test_cafef_crawler.py`

## Key Files

### Deleted
- `backend/app/models/price_alert.py`

### Created
- `backend/alembic/versions/015_remove_price_alerts_and_source.py`

### Modified
- `backend/app/models/__init__.py`
- `backend/app/models/news_article.py`
- `backend/app/crawlers/cafef_crawler.py`
- `backend/app/telegram/formatter.py`
- `backend/app/telegram/handlers.py`
- `backend/app/telegram/services.py`
- `backend/app/scheduler/jobs.py`
- `backend/app/scheduler/manager.py`
- `backend/tests/test_telegram.py`
- `backend/tests/test_scheduler.py`
- `backend/tests/test_cafef_crawler.py`
