---
phase: 109
plan: 01
subsystem: backend/simulator-review
tags: [ai-review, gemini, comparison, simulator]
dependency_graph:
  requires: [peer_analysis_service, simulator_service, ai_analysis_service]
  provides: [simulator_review_service, review_endpoints, comparison_endpoint]
  affects: [frontend-review-ui, frontend-comparison-chart]
tech_stack:
  added: [cachetools.TTLCache]
  patterns: [gemini-structured-output, vietnamese-prompts, ttl-cache, gemini-lock-serialization]
key_files:
  created:
    - backend/app/schemas/simulator_review.py
    - backend/app/services/simulator_review_service.py
    - backend/tests/test_simulator_review.py
  modified:
    - backend/app/api/simulator.py
    - backend/app/schemas/simulator.py
decisions:
  - "Followed peer_analysis_service.py pattern for Gemini integration"
  - "TTLCache maxsize=4 to cover ai + user + buffer"
  - "Only SELL trades reviewable (they have P&L data)"
  - "Trade ownership validated against portfolio_id (T-109-01 mitigation)"
metrics:
  duration: "~8 min"
  completed: "2025-05-15"
  tasks_completed: 2
  tasks_total: 2
  test_count: 11
  files_changed: 5
---

# Phase 109 Plan 01: AI Review Service + Performance Comparison Summary

Gemini-powered portfolio/trade review service with Vietnamese structured output and side-by-side AI vs User comparison endpoint, using TTLCache 300s and _gemini_lock RPM serialization.

## Completed Tasks

| # | Task | Commit | Key Files |
|---|------|--------|-----------|
| 1 | Pydantic schemas + SimulatorReviewService | `d85b1b9` | `simulator_review.py`, `simulator_review_service.py` |
| 2 | API endpoints + comparison schema + tests | `1e5dbc1` | `simulator.py` (api + schemas), `test_simulator_review.py` |

## What Was Built

### Schemas (`backend/app/schemas/simulator_review.py`)
- **PortfolioReviewResponse**: overall_assessment, strengths, weaknesses, suggestions, risk_assessment, score (1-10)
- **TradeReviewResponse**: entry_analysis, exit_analysis, what_went_well, what_could_improve, pattern_identified, overall_verdict
- **ComparisonResponse** (in `simulator.py`): ai/user equity histories, stats, portfolio summaries

### Service (`backend/app/services/simulator_review_service.py`)
- `review_portfolio(portfolio_name)` — fetches portfolio + stats + recent trades → builds Vietnamese prompt → Gemini structured output → cached 300s
- `review_trade(trade_id, portfolio_name)` — validates trade ownership + SELL-only → builds Vietnamese prompt → Gemini structured output
- Uses `_gemini_lock` from `ai_analysis_service` for RPM serialization
- Module-level `TTLCache(maxsize=4, ttl=300)` for portfolio reviews

### Endpoints (`backend/app/api/simulator.py`)
- `POST /simulator/review/portfolio?portfolio_type=user|ai` — Gemini portfolio review
- `POST /simulator/review/trade/{trade_id}?portfolio_type=user|ai` — Gemini trade review
- `GET /simulator/comparison` — side-by-side AI vs User equity + stats + summaries

### Tests (`backend/tests/test_simulator_review.py`)
11 tests: schema validation (3), endpoint validation (2), system instruction (1), TTLCache (1), route registration (3), empty lists (1)

## Deviations from Plan

None — plan executed exactly as written.

## Verification Results

- ✅ `python -m pytest tests/test_simulator_review.py -x -v` — 11/11 passed
- ✅ `python -m pytest tests/ -x -q` — 561/561 passed (no regressions)
- ✅ All 3 new routes registered on router

## Self-Check: PASSED
