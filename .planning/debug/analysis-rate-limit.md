---
status: awaiting_human_verify
trigger: "analysis-rate-limit: concurrent analysis triggers compete for Gemini API rate limit"
created: 2025-01-20T10:00:00Z
updated: 2025-01-20T10:10:00Z
---

## Current Focus

hypothesis: CONFIRMED — concurrent background tasks competing for Gemini rate limit, plus 503 errors not retried at batch level
test: Fix applied — module-level asyncio.Lock + ServerError batch retry
expecting: User triggers multiple analysis types and they queue instead of competing
next_action: Awaiting human verification that concurrent triggers now serialize properly

## Symptoms

expected: When triggering all analysis types, each should complete for all 400 tickers within reasonable time. The summary endpoint for any ticker should return populated analysis data after triggers complete.
actual: Concurrent analysis runs compete for Gemini API rate limit. Technical batch 8/16 and sentiment batch 9/16 are both stuck in 429 retry loops (5 retries × 59s waits). Some sentiment batches failed with 503 errors. ACL and many tickers have null data after 10+ minutes.
errors: Multiple "Batch N hit 429 rate limit" warnings. Multiple "Batch N failed — ServerError: 503 UNAVAILABLE. This model is currently experiencing high demand" errors. All from ai_analysis_service.py.
reproduction: POST to /api/analysis/trigger/ai, /api/analysis/trigger/sentiment, and /api/analysis/trigger/combined in quick succession. Watch logs — they all start concurrently and compete for rate limit.
started: Design issue — trigger endpoints all use BackgroundTasks which run concurrently with no serialization.

## Eliminated

(none yet — root cause identified on first pass)

## Evidence

- timestamp: 2025-01-20T10:00:00Z
  checked: analysis.py trigger endpoints (lines 46-130)
  found: Four POST endpoints each use background_tasks.add_task(_run) — when triggered concurrently, each spawns an independent background task calling analyze_all_tickers()
  implication: No serialization between concurrent triggers — all compete for Gemini rate limit

- timestamp: 2025-01-20T10:01:00Z
  checked: ai_analysis_service.py _run_batched_analysis (lines 239-368)
  found: Each batch loop handles 429 with retry+wait at batch level, but 503 (ServerError) only handled by tenacity @retry on _call_gemini (2 attempts). After that, ServerError falls to generic Exception handler → batch skipped entirely.
  implication: 503 errors from overloaded Gemini model cause permanent batch failures instead of retrying

- timestamp: 2025-01-20T10:02:00Z
  checked: config.py (lines 54-59)
  found: gemini_delay_seconds=60.0, gemini_batch_size=25 — 400 tickers = 16 batches × 60s = ~16 min per analysis type. Three concurrent types = 48 batches competing = 3× the rate limit pressure
  implication: Confirms concurrent runs are unsustainable on free tier

## Resolution

root_cause: Two issues: (1) No serialization between concurrent analysis triggers — each POST endpoint spawns independent background task, all competing for same Gemini rate limit. (2) 503 ServerError from Gemini not retried at batch level — only tenacity @retry with 2 attempts on _call_gemini, after which the batch is permanently failed.
fix: (1) Add module-level asyncio.Lock in ai_analysis_service.py so analyze_all_tickers() acquires it — concurrent triggers queue instead of competing. (2) Add ServerError/503 handling at batch retry level with progressive backoff, matching existing 429 pattern.
verification: pending
files_changed: [backend/app/services/ai_analysis_service.py]
