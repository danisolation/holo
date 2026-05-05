---
phase: 61-ai-rumor-scoring
fixed_at: 2025-07-25T21:00:00Z
review_path: .planning/phases/61-ai-rumor-scoring/61-REVIEW.md
iteration: 1
findings_in_scope: 3
fixed: 3
skipped: 0
status: all_fixed
---

# Phase 61: Code Review Fix Report

**Fixed at:** 2025-07-25T21:00:00Z
**Source review:** .planning/phases/61-ai-rumor-scoring/61-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 3
- Fixed: 3
- Skipped: 0

## Fixed Issues

### WR-01: Bracket Mismatch in `_build_prompt` — Format Differs From Few-Shot Example

**Files modified:** `backend/app/services/rumor_scoring_service.py`, `backend/tests/test_rumor_scoring_service.py`
**Commit:** 93f3728
**Applied fix:** Changed `auth_tag = "[Xác thực ✓]"` (pre-wrapped with brackets) to `auth_label = "Xác thực ✓"` (bare label), and updated the format string to `[{auth_label} | {likes} likes | {replies} replies]` — now matches the few-shot example pattern in `rumor_prompts.py:46`. Updated tests to assert the correct bracket format.

### WR-02: No Date Filter on Rumors Query — All Historical Posts Sent to Gemini

**Files modified:** `backend/app/services/rumor_scoring_service.py`
**Commit:** 93f3728
**Applied fix:** Added `AND posted_at >= CURRENT_DATE - INTERVAL '7 days'` to the rumors SELECT query in `score_ticker`. This limits the scoring window to the last 7 days, preventing unbounded prompt growth and stale data.

### WR-03: Prompt Injection Risk — Raw User Content Interpolated Into LLM Prompt

**Files modified:** `backend/app/services/rumor_scoring_service.py`, `backend/tests/test_rumor_scoring_service.py`
**Commit:** 93f3728
**Applied fix:** Added `_sanitize_content(content, max_len=500)` method that truncates user content to 500 chars and replaces double-quotes with single-quotes. Called in `_build_prompt` before interpolation. Added `test_build_prompt_truncates_long_content` test to verify truncation.

---

_Fixed: 2025-07-25T21:00:00Z_
_Fixer: the agent (gsd-code-fixer)_
_Iteration: 1_
