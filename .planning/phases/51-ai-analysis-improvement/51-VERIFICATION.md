---
phase: 51-ai-analysis-improvement
verified: 2026-04-24T15:17:46Z
status: human_needed
score: 3/3 must-haves verified
overrides_applied: 0
human_verification:
  - test: "Open a ticker detail page (e.g., /ticker/VNM) that has recent combined analysis data with raw_response"
    expected: "Combined recommendation card shows 4 labeled sections (Tóm tắt, Mức giá quan trọng, Rủi ro, Hành động cụ thể) each with its own icon and heading, separated by visual dividers — not a single block of text"
    why_human: "Visual rendering, layout, icon display, and section separation cannot be verified programmatically"
  - test: "Trigger a new combined analysis run and check the AI output for any ticker"
    expected: "Each of the 4 fields (summary, key_levels, risks, action) contains multi-sentence Vietnamese text — not truncated, not a single short line"
    why_human: "AI output quality depends on Gemini model behavior with the new prompts/token limits — cannot verify without running analysis"
  - test: "Open a ticker that only has OLD combined analysis (before Phase 51, no raw_response)"
    expected: "Card falls back to plain text reasoning display — no errors, no blank card"
    why_human: "Backward compatibility with legacy data requires testing against actual old DB records"
---

# Phase 51: AI Analysis Improvement Verification Report

**Phase Goal:** AI analysis output is longer, structured into clear sections, and rendered on the frontend with visual hierarchy — not a plain text block
**Verified:** 2026-04-24T15:17:46Z
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | AI analysis output includes distinct sections (tóm tắt, mức giá quan trọng, rủi ro, hành động cụ thể) — each clearly labeled and separated | ✓ VERIFIED | `TickerCombinedAnalysis` schema has 4 fields: `summary`, `key_levels`, `risks`, `action` (schemas/analysis.py:101-104). Prompt instructs per-field output (prompts.py:55-71). Reasoning extraction concatenates with `## Tóm tắt`, `## Mức giá quan trọng`, `## Rủi ro`, `## Hành động cụ thể` markdown headers (ai_analysis_service.py:509-514). |
| 2 | Batch sizes are reduced and token/thinking limits increased, producing multi-paragraph analysis for every ticker without output truncation | ✓ VERIFIED | `gemini_batch_size=15` (config.py:57), `combined_thinking_budget=2048` (config.py:91), `combined_max_tokens=32768` (config.py:92). Both `_call_gemini` calls in `analyze_combined_batch` pass these values (gemini_client.py:213-214, 227-228). |
| 3 | The frontend renders AI analysis as structured sections with headings and visual separation, replacing the previous plain text block display | ✓ VERIFIED | `StructuredCombinedCard` component renders 4 sections with Vietnamese headings (Tóm tắt, Mức giá quan trọng, Rủi ro, Hành động cụ thể) and icons (FileText, DollarSign, AlertTriangle, Zap) via `COMBINED_SECTIONS` config (analysis-card.tsx:291-296). Uses `<Separator />` between header and sections (line 323). `getStructuredData` validates raw_response fields (lines 271-289). Ticker page imports `StructuredCombinedCard` (page.tsx:37) and renders it (page.tsx:296). Old `CombinedRecommendationCard` no longer referenced from ticker page. Fallback to plain `analysis.reasoning` when raw_response absent (lines 340-344). |

**Score:** 3/3 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `backend/app/config.py` | Reduced batch size and combined analysis token limits | ✓ VERIFIED | `gemini_batch_size: int = 15`, `combined_thinking_budget: int = 2048`, `combined_max_tokens: int = 32768` — all present |
| `backend/app/schemas/analysis.py` | Structured combined analysis schema with 4 section fields | ✓ VERIFIED | `summary`, `key_levels`, `risks`, `action` fields in `TickerCombinedAnalysis`. `explanation` field removed. |
| `backend/app/services/analysis/prompts.py` | Updated combined prompt with section instructions and few-shot | ✓ VERIFIED | `COMBINED_SYSTEM_INSTRUCTION` lists all 4 field instructions. `COMBINED_FEW_SHOT` has comprehensive multi-section example. |
| `backend/app/services/analysis/gemini_client.py` | Combined batch analyzer passing increased token limits | ✓ VERIFIED | `settings.combined_max_tokens` and `settings.combined_thinking_budget` used in both primary and retry `_call_gemini` calls |
| `backend/app/services/ai_analysis_service.py` | Updated reasoning extraction joining 4 sections | ✓ VERIFIED | Lines 509-514: concatenation with markdown headers for all 4 sections. Old `analysis.explanation` reference eliminated. |
| `backend/app/api/analysis.py` | Summary endpoint exposing raw_response for combined | ✓ VERIFIED | `raw_response=analysis.raw_response` in `get_combined_analysis` (line 343). `raw_response=row["raw_response"]` in `get_analysis_summary` (line 411). |
| `frontend/src/lib/api.ts` | AnalysisResult with raw_response and StructuredCombined interface | ✓ VERIFIED | `raw_response?: Record<string, unknown> \| null` in AnalysisResult (line 66). `StructuredCombinedData` interface (lines 70-75). |
| `frontend/src/components/analysis-card.tsx` | StructuredCombinedCard component rendering 4 sections | ✓ VERIFIED | Component at lines 299-355. 4 sections with icons, Vietnamese labels, separator, and fallback. |
| `frontend/src/app/ticker/[symbol]/page.tsx` | Ticker page using StructuredCombinedCard for combined analysis | ✓ VERIFIED | Import at line 37, rendered at line 296. `CombinedRecommendationCard` no longer imported. |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `schemas/analysis.py` | `gemini_client.py` | CombinedBatchResponse used as response_schema | ✓ WIRED | Imported at line 21, used as response_schema in all 3 Gemini calls |
| `gemini_client.py` | `config.py` | settings.combined_max_tokens / settings.combined_thinking_budget | ✓ WIRED | 4 references: lines 213, 214, 227, 228 |
| `api/analysis.py` | `schemas/analysis.py` | AnalysisResultResponse includes raw_response | ✓ WIRED | raw_response passed in combined endpoint (line 343) and summary endpoint (line 411) |
| `analysis-card.tsx` | `api.ts` | StructuredCombinedData type imported | ✓ WIRED | Import at line 4, used in getStructuredData return type |
| `ticker/[symbol]/page.tsx` | `analysis-card.tsx` | StructuredCombinedCard imported and rendered | ✓ WIRED | Import at line 37, rendered at line 296 |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|--------------|--------|--------------------|--------|
| `analysis-card.tsx` (StructuredCombinedCard) | `analysis` prop → `structured` via `getStructuredData` | `analysisSummary.combined` from `useAnalysisSummary` hook → `fetchAnalysisSummary` → GET `/analysis/{symbol}/summary` API → DB query with raw_response | Yes — DB window query returns `raw_response` JSONB column which contains AI-generated structured data | ✓ FLOWING |
| `analysis-card.tsx` (fallback) | `analysis.reasoning` | Same API path, `reasoning` TEXT column from DB | Yes — DB query returns reasoning column which stores markdown-concatenated sections | ✓ FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Schema has 4 structured fields | `grep "summary\|key_levels\|risks\|action" backend/app/schemas/analysis.py` | All 4 fields found in TickerCombinedAnalysis (lines 101-104) | ✓ PASS |
| Batch size reduced | `grep "gemini_batch_size" backend/app/config.py` | `gemini_batch_size: int = 15` | ✓ PASS |
| Token limits configured | `grep "combined_" backend/app/config.py` | `combined_thinking_budget: int = 2048`, `combined_max_tokens: int = 32768` | ✓ PASS |
| Frontend StructuredCombinedCard exported | `grep "StructuredCombinedCard" frontend/src/components/analysis-card.tsx` | Found at lines 4, 271, 299 (import, helper, component def) | ✓ PASS |
| Ticker page uses new card | `grep "StructuredCombinedCard" frontend/src/app/ticker/\[symbol\]/page.tsx` | Found at lines 37, 296 | ✓ PASS |
| Old card NOT in ticker page | `grep "CombinedRecommendationCard" frontend/src/app/ticker/\[symbol\]/page.tsx` | No matches | ✓ PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| AI-01 | 51-01-PLAN | AI analysis output dài hơn với sections rõ ràng (tóm tắt, mức giá quan trọng, rủi ro, hành động cụ thể) | ✓ SATISFIED | Pydantic schema has 4 fields; prompts instruct detailed per-field output; reasoning stored with markdown section headers |
| AI-02 | 51-01-PLAN | Giảm batch size + tăng token/thinking limits cho output chất lượng hơn | ✓ SATISFIED | batch 25→15; combined_max_tokens=32768; combined_thinking_budget=2048; both Gemini calls use these |
| AI-03 | 51-02-PLAN | Frontend render AI output dạng structured sections với headings thay vì plain text block | ✓ SATISFIED | StructuredCombinedCard renders 4 sections with Vietnamese headings, icons, Separator; ticker page wired; fallback preserved |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `frontend/src/lib/api.ts` | 269 | `return null` | ℹ️ Info | Expected 404 error handling for missing trading signal — not a stub |
| `frontend/src/components/analysis-card.tsx` | 288 | `return null` | ℹ️ Info | `getStructuredData` returns null when raw_response is invalid — intentional fallback trigger, not a stub |

No TODO, FIXME, placeholder, or blocking anti-patterns found in any modified file.

### Human Verification Required

### 1. Visual Section Rendering

**Test:** Open a ticker detail page (e.g., /ticker/VNM) that has recent combined analysis data with `raw_response`
**Expected:** Combined recommendation card shows 4 labeled sections (Tóm tắt, Mức giá quan trọng, Rủi ro, Hành động cụ thể) each with its own icon and heading, separated by visual dividers — not a single block of text
**Why human:** Visual rendering, layout, icon display, and section separation cannot be verified programmatically

### 2. AI Output Quality

**Test:** Trigger a new combined analysis run and check the AI output for any ticker
**Expected:** Each of the 4 fields (summary, key_levels, risks, action) contains multi-sentence Vietnamese text — not truncated, not a single short line
**Why human:** AI output quality depends on Gemini model behavior with the new prompts/token limits — cannot verify without running analysis

### 3. Backward Compatibility

**Test:** Open a ticker that only has OLD combined analysis (before Phase 51, no `raw_response`)
**Expected:** Card falls back to plain text reasoning display — no errors, no blank card
**Why human:** Backward compatibility with legacy data requires testing against actual old DB records

### Gaps Summary

No automated gaps found. All 3 success criteria verified at code level. All 3 requirements (AI-01, AI-02, AI-03) satisfied with concrete evidence. All key links wired and data flowing.

Human verification is needed for:
1. Visual appearance of the 4-section structured card
2. Actual AI output quality with new prompts/token limits
3. Backward compatibility with old data lacking raw_response

---

_Verified: 2026-04-24T15:17:46Z_
_Verifier: the agent (gsd-verifier)_
