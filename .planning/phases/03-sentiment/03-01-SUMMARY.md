---
phase: 03-sentiment
plan: 01
subsystem: sentiment-foundation
tags: [models, schemas, migration, config, dependencies]
dependency_graph:
  requires: [02-01-PLAN, 02-02-PLAN, 02-03-PLAN]
  provides: [NewsArticle-model, sentiment-schemas, combined-schemas, migration-003]
  affects: [03-02-PLAN, 03-03-PLAN]
tech_stack:
  added: [beautifulsoup4]
  patterns: [ORM-model, Alembic-raw-DDL, Pydantic-Gemini-schema, ENUM-extension]
key_files:
  created:
    - backend/app/models/news_article.py
    - backend/alembic/versions/003_sentiment_tables.py
  modified:
    - backend/app/models/ai_analysis.py
    - backend/app/models/__init__.py
    - backend/app/schemas/analysis.py
    - backend/app/config.py
    - backend/requirements.txt
    - backend/.env.example
decisions:
  - "html.parser over lxml: built-in stdlib parser sufficient for ~30 small CafeF elements; no extra C dependency"
  - "Index on (ticker_id, published_at DESC) via raw DDL in migration rather than ORM __table_args__ to avoid SQLAlchemy class-level .desc() issues"
  - "beautifulsoup4>=4.12,<5: conservative range covering vnstock transitive dep version while making it explicit"
metrics:
  duration: 3m
  completed: 2026-04-15
  tasks_completed: 2
  tasks_total: 2
  files_changed: 8
requirements: [AI-03, AI-04, AI-05, AI-06]
---

# Phase 3 Plan 1: Sentiment Foundation — Models, Schemas & Migration Summary

**One-liner:** NewsArticle ORM model + Alembic migration 003 (news_articles table, COMBINED enum) + Pydantic schemas for sentiment/combined Gemini responses + beautifulsoup4 dependency + CafeF config settings.

## What Was Built

### Task 1: NewsArticle model, AnalysisType update, migration 003, deps & config
**Commit:** `36d380b`

- **NewsArticle ORM model** (`backend/app/models/news_article.py`): BigSerial PK, ticker_id FK, title (Text), url (VARCHAR 500), published_at (TIMESTAMPTZ), source (VARCHAR 20, default 'cafef'), created_at. UniqueConstraint on (ticker_id, url).
- **AnalysisType enum** updated with `COMBINED = "combined"` value in `ai_analysis.py`.
- **`__init__.py`** exports NewsArticle alongside all existing models.
- **Migration 003** (`003_sentiment_tables.py`): `ALTER TYPE analysis_type ADD VALUE IF NOT EXISTS 'combined'` + `CREATE TABLE news_articles` with index on (ticker_id, published_at DESC).
- **requirements.txt**: Added `beautifulsoup4>=4.12,<5` as explicit dependency (was only transitive via vnstock).
- **config.py**: Added `cafef_delay_seconds: float = 1.0` and `cafef_news_days: int = 7`.
- **.env.example**: Added CafeF News Scraping section with CAFEF_DELAY_SECONDS and CAFEF_NEWS_DAYS.

### Task 2: Pydantic schemas for sentiment and combined Gemini responses
**Commit:** `350d749`

Extended `backend/app/schemas/analysis.py` with:
- **SentimentLevel** enum: very_positive, positive, neutral, negative, very_negative
- **TickerSentimentAnalysis**: ticker, sentiment, score (1-10), reasoning
- **SentimentBatchResponse**: analyses list (Gemini batch response schema)
- **Recommendation** enum: mua, ban, giu (Vietnamese buy/sell/hold)
- **TickerCombinedAnalysis**: ticker, recommendation, confidence (1-10), explanation
- **CombinedBatchResponse**: analyses list (Gemini batch response schema)
- **SummaryResponse**: ticker_symbol + 4 optional AnalysisResultResponse fields (technical, fundamental, sentiment, combined)

## Verification Results

| Check | Result |
|-------|--------|
| `from app.models import NewsArticle, AnalysisType; assert hasattr(AnalysisType, 'COMBINED')` | ✅ PASS |
| `from app.schemas.analysis import SentimentBatchResponse, CombinedBatchResponse, SummaryResponse` | ✅ PASS |
| `grep beautifulsoup4 requirements.txt` returns 1 | ✅ PASS |
| `grep cafef_delay_seconds config.py` returns 1 | ✅ PASS |
| Migration 003 has ALTER TYPE + CREATE TABLE | ✅ PASS |

## Deviations from Plan

None — plan executed exactly as written.

## Decisions Made

1. **html.parser over lxml**: Plan explicitly said "Do NOT add lxml" — `html.parser` (built-in) is sufficient for parsing ~30 small HTML elements per CafeF page. No extra C dependency needed.
2. **Index via DDL only**: The `(ticker_id, published_at DESC)` index is created in migration raw SQL rather than in ORM `__table_args__` to avoid SQLAlchemy `mapped_column.desc()` class-level resolution issues. The UniqueConstraint remains in ORM for SQLAlchemy metadata awareness.
3. **beautifulsoup4 range**: Used `>=4.12,<5` — conservative range that covers the 4.14.3 version installed as vnstock transitive dependency.

## Known Stubs

None — all models, schemas, and config are fully wired with real types and defaults.
