---
status: awaiting_human_verify
trigger: "ALL AI analysis endpoints under /api/analysis/{symbol}/... return HTTP 500 Internal Server Error"
created: 2025-01-28T12:00:00Z
updated: 2025-01-28T12:45:00Z
---

## Current Focus

hypothesis: CONFIRMED — Missing `values_callable` in SAEnum causes SQLAlchemy to send uppercase enum names ('TECHNICAL') instead of lowercase PostgreSQL values ('technical')
test: Reproduced by reverting the fix → 500s returned. Restored fix → 200s returned.
expecting: N/A — root cause confirmed and verified
next_action: Awaiting human verification that the server restart + exception handler fix resolves the issue

## Symptoms

expected: GET /api/analysis/ACL/summary (and /technical, /fundamental, /sentiment, /combined) should return JSON analysis data or 404
actual: All return HTTP 500 with plain text "Internal Server Error" (21 bytes, text/plain). No JSON error detail.
errors: HTTP 500 Internal Server Error on all AI analysis endpoints. No traceback visible in response.
reproduction: curl http://localhost:8080/api/analysis/ACL/summary → 500. Same for all analysis types and tickers.
started: Unknown. Indicators endpoint works fine. Issue isolated to endpoints querying AIAnalysis model.

## Eliminated

- hypothesis: Database ENUM has only 3 values (missing 'combined')
  evidence: Migration 003 adds 'combined' with ALTER TYPE. And fresh server queries work for all 4 types.
  timestamp: 2025-01-28T12:05:00Z

- hypothesis: SQLAlchemy model schema doesn't match table (column mismatch)
  evidence: Direct Python queries against the model work perfectly (25 rows loaded successfully)
  timestamp: 2025-01-28T12:10:00Z

- hypothesis: FastAPI response_model validation failing
  evidence: TestClient with response_model returns 200. AnalysisResultResponse constructs correctly.
  timestamp: 2025-01-28T12:15:00Z

- hypothesis: Database connection pool exhaustion or stale connections
  evidence: Indicators endpoint uses same async_session pool and works fine
  timestamp: 2025-01-28T12:15:00Z

- hypothesis: Uvicorn --reload causing the issue
  evidence: Fresh server with --reload works fine. Issue was the stale running server not picking up the fix.
  timestamp: 2025-01-28T12:30:00Z

## Evidence

- timestamp: 2025-01-28T12:00:00Z
  checked: Migration 002 vs 003 vs AIAnalysis model
  found: Migration 002 creates ENUM with 3 values. Migration 003 adds 'combined'. Model has 4 values. All match.
  implication: ENUM mismatch is not the issue (migration 003 was applied)

- timestamp: 2025-01-28T12:05:00Z
  checked: Direct Python query against AIAnalysis table
  found: 25 rows exist, all with analysis_type=TECHNICAL. Queries work, data loads, AnalysisResultResponse constructs correctly.
  implication: Code logic is correct. Issue is NOT in the endpoint code itself.

- timestamp: 2025-01-28T12:10:00Z
  checked: FastAPI TestClient with original code
  found: TestClient returns 200 for VCB/technical. Full response body is correct JSON.
  implication: The code works. The issue is specific to the RUNNING server instance, not the code.

- timestamp: 2025-01-28T12:15:00Z
  checked: Fresh server start (without --reload)
  found: All endpoints return correct responses (200 or 404, no 500s)
  implication: The original running server had stale state. Server restart resolves the issue.

- timestamp: 2025-01-28T12:25:00Z
  checked: Git history — commit 528d22b "fix: SQLAlchemy enum values_callable for asyncpg compatibility"
  found: This commit added values_callable to SAEnum(AnalysisType). Without it, SQLAlchemy sends 'TECHNICAL' instead of 'technical' to PostgreSQL.
  implication: The root cause fix was ALREADY committed, but the running server hadn't picked it up.

- timestamp: 2025-01-28T12:30:00Z
  checked: Reproduction test — reverted values_callable, tested, restored
  found: Without values_callable → VCB/technical=500, ACL/summary=500, ACL/indicators=200. With values_callable → all correct.
  implication: ROOT CAUSE CONFIRMED. Missing values_callable causes PostgreSQL to reject uppercase enum names.

## Resolution

root_cause: The SAEnum(AnalysisType) column in AIAnalysis was missing `values_callable=lambda e: [m.value for m in e]`. Without this, SQLAlchemy sends Python enum NAMES ('TECHNICAL', 'FUNDAMENTAL') instead of PostgreSQL enum VALUES ('technical', 'fundamental'). PostgreSQL rejects these invalid enum values with an unhandled exception → bare 500. The fix was committed (528d22b) but the running server hadn't picked it up.
fix: 1) Server restart loads the already-committed values_callable fix. 2) Added global exception handler in main.py to log tracebacks and return JSON errors instead of bare "Internal Server Error" text — prevents this debugging difficulty in the future.
verification: Reproduced 500 by reverting fix, confirmed 200 by restoring. All 8 endpoint variants tested (200 for data, 404 for missing, 0 spurious 500s). Exception handler verified to not break existing 404/200 responses.
files_changed: [backend/app/main.py]
