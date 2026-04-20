# Phase 20: Trading Plan Dashboard Panel - Research

**Researched:** 2026-04-20
**Domain:** Next.js 16 frontend — React component, API integration, TypeScript types
**Confidence:** HIGH

## Summary

Phase 20 is a frontend-dominant phase: build a `TradingPlanPanel` component on the ticker detail page that displays dual-direction (LONG/BEARISH) trading plans with entry/SL/TP targets, R:R ratio, position sizing, timeframe, and Vietnamese rationale. All shadcn primitives (Card, Badge, Skeleton) are already installed. The project follows well-established patterns from the existing `SupportResistanceCard` and `AnalysisCard` components — two-column grid, Vietnamese labels, dense rows, font-mono prices, `ScoreBar` confidence visualization.

**Critical backend gap discovered:** The existing `GET /api/analysis/{symbol}/trading-signal` endpoint returns `AnalysisResultResponse` which only contains `signal`, `score`, `reasoning`, `model_version`. It does **not** return the full `TickerTradingSignal` data (entry prices, SL, TP, R:R, position sizing, timeframe, per-direction confidence/reasoning). This data is stored in the `raw_response` JSONB column but is not exposed in the API response schema. A small backend schema change is required to expose this data before the frontend can consume it.

**Primary recommendation:** Extend the backend `AnalysisResultResponse` with an optional `raw_response: dict | None = None` field (1-line schema change + 1-line endpoint change), then build the frontend panel following the existing `SupportResistanceCard` two-column pattern exactly.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Panel placement: AFTER Combined Recommendation card, BEFORE Analysis Cards grid (full-width, not in 3-column grid)
- Two-column layout: LONG (left), BEARISH (right); recommended direction highlighted with accent border/background
- Each column: direction badge, confidence score (1-10), trading plan details (entry, SL, TP1, TP2, R:R, position %, timeframe), Vietnamese reasoning
- Data flow: fetch from `GET /api/analysis/{symbol}/trading-signal` endpoint (Phase 19)
- Frontend types: `TradingPlanDetail`, `DirectionAnalysis`, `TickerTradingSignal` interfaces; `fetchTradingSignal()` API function
- All Vietnamese labels locked (see Copywriting Contract in UI-SPEC)
- Vietnamese comma price format: `Math.round(v).toLocaleString("vi-VN")`
- Confidence color scale: 7-10 green `#26a69a`, 4-6 yellow `yellow-500`, 1-3 red `#ef5350`, 0 muted
- Invalid signals (score=0): show "Tín hiệu không hợp lệ" with muted styling
- Empty state: "Chưa có kế hoạch giao dịch"
- Error state: panel simply not rendered (matches existing conditional rendering pattern)

### Agent's Discretion
- Exact card styling (shadow, border radius, padding)
- Responsive breakpoint for mobile stacking
- Whether to use tabs or side-by-side columns on mobile (UI-SPEC chose stacking)
- Loading skeleton design (UI-SPEC set `h-[320px]`)
- Animation/transitions (UI-SPEC chose none)

### Deferred Ideas (OUT OF SCOPE)
- Historical trading signal performance tracking — out of v3.0 scope
- Comparison with previous day's signals — future enhancement
- Chart overlay of entry/SL/TP — handled in Phase 21
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| DISP-01 | User can view a Trading Plan panel on the ticker detail page showing full LONG and BEARISH analysis | New `TradingPlanPanel` component, `fetchTradingSignal()` API function, `useTradingSignal()` hook, backend schema extension to expose `raw_response` JSONB data |
</phase_requirements>

## Standard Stack

### Core (already installed — zero new dependencies)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Next.js | 16.2.3 | App framework | Already the project framework [VERIFIED: package.json] |
| React | 19.2.4 | UI library | Already installed [VERIFIED: package.json] |
| @tanstack/react-query | 5.99.0 | Data fetching / caching | Already used for all API hooks [VERIFIED: package.json] |
| shadcn | 4.2.0 | Component primitives (Card, Badge, Skeleton) | Already installed, all needed primitives exist [VERIFIED: ui/ directory] |
| @base-ui/react | 1.4.0 | Base UI primitives | Already installed [VERIFIED: package.json] |
| lucide-react | 1.8.0 | Icons | Already used project-wide [VERIFIED: package.json] |
| Tailwind CSS | 4 | Styling | Already installed [VERIFIED: package.json devDeps] |

### Supporting (already installed)

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| clsx | 2.1.1 | Conditional class merging | Dynamic class composition for direction colors |
| tailwind-merge | 3.5.0 | Tailwind class dedup | Via `cn()` utility already in project |

### No New Installations Required

All dependencies are already installed. **Zero `npm install` commands needed.** [VERIFIED: package.json + ui/ directory listing]

## Architecture Patterns

### Project Structure (existing — no new directories)

```
frontend/src/
├── components/
│   ├── trading-plan-panel.tsx    ← NEW component (single file)
│   ├── analysis-card.tsx         ← REUSE ScoreBar pattern
│   ├── support-resistance-card.tsx ← REUSE two-column + dense rows
│   └── ui/                       ← shadcn primitives (Card, Badge, Skeleton)
├── lib/
│   ├── api.ts                    ← ADD types + fetchTradingSignal()
│   └── hooks.ts                  ← ADD useTradingSignal() hook
└── app/ticker/[symbol]/
    └── page.tsx                  ← INSERT TradingPlanPanel between lines 301-303
```

### Pattern 1: Two-Column Card with Dense Rows (REUSE from SupportResistanceCard)

**What:** Grid layout with column subheading + key-value rows
**When to use:** Displaying structured data in side-by-side columns
**Source:** `support-resistance-card.tsx` lines 137-194 [VERIFIED: codebase]

```tsx
// Exact pattern from support-resistance-card.tsx
<Card>
  <CardHeader>
    <CardTitle className="text-lg font-semibold">Kế Hoạch Giao Dịch</CardTitle>
  </CardHeader>
  <CardContent>
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      {/* Column with subheading */}
      <div>
        <p className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground mb-2">
          LONG
        </p>
        {/* Dense rows */}
        <div className="flex items-center justify-between py-1.5">
          <span className="text-xs font-medium text-muted-foreground">Giá vào</span>
          <span className="font-mono text-sm font-semibold">25,400</span>
        </div>
      </div>
    </div>
  </CardContent>
</Card>
```

### Pattern 2: ScoreBar Confidence Visualization (REUSE from AnalysisCard)

**What:** Horizontal bar with 1-10 score, color-coded by range
**Source:** `analysis-card.tsx` lines 159-177 [VERIFIED: codebase]

```tsx
// Exact pattern from analysis-card.tsx
function ScoreBar({ score }: { score: number }) {
  const pct = Math.min(100, Math.max(0, (score / 10) * 100));
  const color =
    score >= 7 ? "bg-[#26a69a]" : score >= 4 ? "bg-yellow-500" : "bg-[#ef5350]";
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-2 bg-muted rounded-full overflow-hidden">
        <div className={`h-full rounded-full transition-all ${color}`} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-xs font-mono font-bold min-w-[2ch] text-right">{score}</span>
    </div>
  );
}
```

### Pattern 3: API Function + React Query Hook (REUSE from hooks.ts)

**What:** Typed fetch function in `api.ts` + `useQuery` wrapper in `hooks.ts`
**Source:** `api.ts` lines 88-141, `hooks.ts` lines 76-83 [VERIFIED: codebase]

```tsx
// api.ts — same pattern as fetchAnalysisSummary
export async function fetchTradingSignal(symbol: string): Promise<TickerTradingSignal | null> {
  try {
    return await apiFetch<TickerTradingSignal>(
      `/analysis/${encodeURIComponent(symbol)}/trading-signal`
    );
  } catch (e) {
    if (e instanceof ApiError && e.status === 404) return null;
    throw e;
  }
}

// hooks.ts — same pattern as useAnalysisSummary
export function useTradingSignal(symbol: string | undefined) {
  return useQuery({
    queryKey: ["trading-signal", symbol],
    queryFn: () => fetchTradingSignal(symbol!),
    enabled: !!symbol,
    staleTime: 5 * 60 * 1000,  // match existing analysis staleTime
  });
}
```

### Pattern 4: Vietnamese Number Formatting (REUSE from SupportResistanceCard)

**What:** Price formatting with Vietnamese locale comma separator
**Source:** `support-resistance-card.tsx` line 13 [VERIFIED: codebase]

```tsx
const fmt = (v: number) => Math.round(v).toLocaleString("vi-VN");
```

### Pattern 5: Conditional Panel Rendering (REUSE from ticker page)

**What:** Only show panel if data exists; skeleton while loading
**Source:** `page.tsx` lines 295-301 [VERIFIED: codebase]

```tsx
// Existing pattern for Combined Recommendation
{analysisLoading ? (
  <Skeleton className="h-32 rounded-xl" />
) : analysisSummary?.combined ? (
  <section>
    <CombinedRecommendationCard analysis={analysisSummary.combined} />
  </section>
) : null}
```

### Anti-Patterns to Avoid
- **Don't create new directories:** Single component file in existing `components/` directory
- **Don't install new packages:** Everything needed is already installed
- **Don't deviate from existing patterns:** The project has strong pattern consistency — follow `SupportResistanceCard` exactly
- **Don't create a separate loading component:** Use inline `<Skeleton>` like all other cards
- **Don't use client-side data transformation libraries:** Simple inline formatting with `toLocaleString` and template literals

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Score visualization | Custom SVG or canvas | `ScoreBar` from analysis-card.tsx | Already exists, handles color thresholds |
| Card layout | Custom div structure | shadcn Card/CardHeader/CardTitle/CardContent | Consistent with all other cards on page |
| Data fetching/caching | Manual fetch + state | @tanstack/react-query useQuery | Already the project pattern, handles stale/refetch |
| Badge styling | Custom span with colors | shadcn Badge variant="secondary" | Consistent with analysis-card signal badges |
| Loading skeleton | Spinner or custom loader | shadcn Skeleton | Already used on every loading state |
| Number formatting | Custom regex/string manipulation | `Math.round(v).toLocaleString("vi-VN")` | Browser-native, matches existing `fmt()` |

**Key insight:** This phase should produce ZERO novel patterns. Every visual element already exists somewhere on the ticker detail page.

## Common Pitfalls

### Pitfall 1: Backend API Doesn't Expose Full Trading Plan Data
**What goes wrong:** The `GET /api/analysis/{symbol}/trading-signal` endpoint returns `AnalysisResultResponse` which only has `signal, score, reasoning, model_version`. The full trading plan data (entry_price, stop_loss, take_profit_1/2, risk_reward_ratio, position_size_pct, timeframe, per-direction confidence/reasoning) is stored in `raw_response` JSONB but NOT returned by the API.
**Why it happens:** Phase 19 created the endpoint to match the existing `AnalysisResultResponse` schema used by all other analysis types. The full `TickerTradingSignal` data was saved to `raw_response` JSONB for future use.
**How to avoid:** Extend backend before building frontend. Options (simplest first):
1. Add `raw_response: dict | None = None` field to `AnalysisResultResponse` schema + pass `raw_response=analysis.raw_response` in the endpoint — 2 lines changed
2. Create a new `TradingSignalDetailResponse` Pydantic schema that restructures `raw_response` into typed fields
**Warning signs:** Frontend fetches trading signal but only gets signal/score/reasoning without entry/SL/TP details

### Pitfall 2: AnalysisSummary Frontend Type Missing trading_signal
**What goes wrong:** The frontend `AnalysisSummary` type in `api.ts` line 68-74 has `technical`, `fundamental`, `sentiment`, `combined` but does NOT have `trading_signal`.
**Why it happens:** The backend added `trading_signal` to `SummaryResponse` in Phase 19, but the frontend type wasn't updated (Phase 19 was backend-only).
**How to avoid:** Add `trading_signal?: AnalysisResult` to the frontend `AnalysisSummary` interface. This gives the page access to basic signal data (direction + overall score) from the summary, while the dedicated endpoint provides the full plan.
**Warning signs:** TypeScript errors when accessing `analysisSummary.trading_signal`

### Pitfall 3: Invalid Signal State (score=0) Missing Trading Plan
**What goes wrong:** When a trading signal fails validation, `signal="invalid"`, `score=0`, and `trading_plan` data may be incomplete or null in `raw_response`.
**Why it happens:** Validation failure (price out of ATR bounds, etc.) stores `signal="invalid"` with `score=0` and `reasoning="Validation failed: {reason}"`. The `raw_response` still contains the original Gemini output, but it was deemed invalid.
**How to avoid:** Check for `score === 0` or `signal === "invalid"` at the direction level AND at the overall level. For invalid signals, render the "Tín hiệu không hợp lệ" muted state per CONTEXT.md. Don't try to display price rows for invalid directions.
**Warning signs:** NaN or broken prices displayed when direction confidence is 0

### Pitfall 4: Null take_profit_2
**What goes wrong:** `take_profit_2` might not always be present in the data from Gemini.
**Why it happens:** The backend schema defines `take_profit_2: float` (required), but the UI-SPEC `TradingPlanDetail` interface specifies `take_profit_2: number | null`. Gemini might return 0 or a close-to-entry value.
**How to avoid:** Handle `take_profit_2` being null or 0 gracefully — only show TP2 row if value is meaningful (non-null, non-zero). The backend Pydantic schema requires it (`float`), so it will always be present but may equal `take_profit_1`.
**Warning signs:** TP2 row showing same value as TP1 or showing 0

### Pitfall 5: Page.tsx Insertion Point
**What goes wrong:** Inserting the panel at the wrong location in the ticker detail page.
**Why it happens:** Line numbers shift as code is modified. The panel must go AFTER the Combined Recommendation section (currently lines 294-301) and BEFORE the Analysis Cards Grid section (currently lines 303-350).
**How to avoid:** Search for `<CombinedRecommendationCard` and `Phân tích AI đa chiều` markers. Insert the trading plan panel section between these two sections.
**Warning signs:** Panel appears inside the wrong section or after analysis cards

### Pitfall 6: Race Condition Between Summary and Trading Signal Fetches
**What goes wrong:** The page fetches `analysisSummary` and `tradingSignal` independently. If trading signal data exists but analysisSummary doesn't include combined, the panel might render without context.
**Why it happens:** Two separate React Query hooks with different query keys.
**How to avoid:** The trading plan panel should render independently of `analysisSummary`. Use its own `useTradingSignal(symbol)` hook. Show/hide based solely on the trading signal data availability, not the combined recommendation's existence.
**Warning signs:** Panel appears/disappears based on unrelated data loading

## Code Examples

### Complete Data Flow Pattern

```tsx
// 1. Types in api.ts [follows existing pattern]
export interface TradingPlanDetail {
  entry_price: number;
  stop_loss: number;
  take_profit_1: number;
  take_profit_2: number;
  risk_reward_ratio: number;
  position_size_pct: number;
  timeframe: "swing" | "position";
}

export interface DirectionAnalysis {
  direction: "long" | "bearish";
  confidence: number;          // 0-10
  trading_plan: TradingPlanDetail;
  reasoning: string;           // Vietnamese text
}

export interface TickerTradingSignal {
  ticker: string;
  recommended_direction: "long" | "bearish";
  long_analysis: DirectionAnalysis;
  bearish_analysis: DirectionAnalysis;
}

// 2. Fetch function in api.ts [pattern from fetchAnalysisSummary]
export async function fetchTradingSignal(symbol: string): Promise<TickerTradingSignal | null> {
  try {
    // Endpoint returns AnalysisResultResponse with raw_response containing full signal data
    const result = await apiFetch<AnalysisResult & { raw_response?: TickerTradingSignal }>(
      `/analysis/${encodeURIComponent(symbol)}/trading-signal`
    );
    return result.raw_response ?? null;
  } catch (e) {
    if (e instanceof ApiError && e.status === 404) return null;
    throw e;
  }
}

// 3. Hook in hooks.ts [pattern from useAnalysisSummary]
export function useTradingSignal(symbol: string | undefined) {
  return useQuery({
    queryKey: ["trading-signal", symbol],
    queryFn: () => fetchTradingSignal(symbol!),
    enabled: !!symbol,
    staleTime: 5 * 60 * 1000,
  });
}
```

### Direction Column Rendering Pattern

```tsx
// Recommended column highlight (per UI-SPEC)
const isRecommended = direction === data.recommended_direction;
const directionColor = direction === "long" ? "#26a69a" : "#ef5350";

<div className={cn(
  "rounded-lg p-3",
  isRecommended && `border-l-2 border-[${directionColor}] bg-[${directionColor}]/5`
)}>
  {/* Column subheading with optional "Khuyến nghị" badge */}
  <div className="flex items-center gap-2 mb-2">
    <p className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
      {direction === "long" ? "LONG" : "XU HƯỚNG GIẢM"}
    </p>
    {isRecommended && (
      <Badge variant="secondary" className={`text-[${directionColor}] bg-[${directionColor}]/10 text-[10px]`}>
        Khuyến nghị
      </Badge>
    )}
  </div>
</div>
```

### Price Row Pattern (Dense Row Reuse)

```tsx
// Exact reuse of support-resistance-card dense row pattern
const fmt = (v: number) => Math.round(v).toLocaleString("vi-VN");

<div className="flex items-center justify-between py-1.5">
  <span className="text-xs font-medium text-muted-foreground">Giá vào</span>
  <span className="font-mono text-sm font-semibold">{fmt(plan.entry_price)}</span>
</div>
<div className="flex items-center justify-between py-1.5">
  <span className="text-xs font-medium text-muted-foreground">Cắt lỗ</span>
  <span className="font-mono text-sm font-semibold text-[#ef5350]">{fmt(plan.stop_loss)}</span>
</div>
```

### Page Integration Pattern

```tsx
// In page.tsx — insert AFTER CombinedRecommendationCard, BEFORE Analysis Cards Grid
// Search for: </section> after CombinedRecommendationCard

{/* Trading Plan Panel — Phase 20 */}
{tradingSignalLoading ? (
  <Skeleton className="h-[320px] rounded-xl" />
) : tradingSignal ? (
  <section>
    <TradingPlanPanel data={tradingSignal} />
  </section>
) : null}

{/* Analysis Cards Grid — existing */}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| shadcn v0 (Radix) | shadcn v4 (@base-ui/react) | 2025 | Project already on v4.2.0 — no migration needed |
| React 18 | React 19 | 2025 | Project already on 19.2.4 — use `use()` hook for params |
| Next.js Pages Router | Next.js App Router | 2023+ | Project uses App Router — async params with `use()` |

**Nothing deprecated or outdated** in the current stack for this phase's needs.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Backend `raw_response` JSONB contains full `TickerTradingSignal` model_dump() for all trading signal records | Pitfall 1 / Code Examples | HIGH — if raw_response is null or differently structured, frontend can't display prices. Verified by code at service line 680: `raw_response=analysis.model_dump()` |
| A2 | The `AnalysisResultResponse` schema can be extended with `raw_response: dict | None = None` without breaking other endpoints | Pitfall 1 | LOW — Pydantic optional fields with None default are backward-compatible, and other analysis types simply don't populate it |
| A3 | `ScoreBar` component can be imported from analysis-card.tsx or must be duplicated | Pattern 2 | LOW — if not exported, the function is small enough to copy into trading-plan-panel.tsx |

**Note on A1:** Line 680 of `ai_analysis_service.py` confirms `raw_response=analysis.model_dump()` is called for trading signals, where `analysis` is the parsed `TickerTradingSignal` Pydantic model. This is VERIFIED from codebase, not assumed. The assumption is that all existing records in production have this data populated.

## Open Questions

1. **Backend schema extension approach**
   - What we know: `AnalysisResultResponse` doesn't include `raw_response`. The full trading plan data is stored in JSONB.
   - What's unclear: Should we add `raw_response` to the generic `AnalysisResultResponse` (affects all analysis types) or create a `TradingSignalDetailResponse` (cleaner but more code)?
   - Recommendation: Add optional `raw_response: dict | None = None` to `AnalysisResultResponse` — it's backward-compatible (None for existing types), requires only 2 lines of backend change, and keeps the endpoint URL the same. Then populate it only in the trading-signal endpoint handler.

2. **ScoreBar export availability**
   - What we know: `ScoreBar` is defined inside `analysis-card.tsx` (line 159) but is not exported from the module.
   - What's unclear: Should we export it as a shared utility or duplicate the 15-line function?
   - Recommendation: Export `ScoreBar` from `analysis-card.tsx` and import it in `trading-plan-panel.tsx`. It's the same visualization needed.

3. **Confidence=0 vs Direction-level confidence**
   - What we know: The backend stores overall `score` (recommended direction's confidence) in the flat response. Per-direction confidence is inside `raw_response`.
   - What's unclear: Can one direction have confidence=0 while the other is valid?
   - Recommendation: The backend `DirectionAnalysis.confidence` has `ge=1` (minimum 1), so a direction always has confidence ≥1. Only the overall signal can be `score=0` (validation failure). Handle per-direction display using the `raw_response` data; handle overall invalid state using the flat `score` field.

## Environment Availability

Step 2.6: SKIPPED (no external dependencies identified). This phase is purely frontend code/config changes within an existing Next.js application. All tools (Node.js, npm, Next.js) are already available as the project is actively developed.

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | None detected — no frontend test framework configured |
| Config file | none |
| Quick run command | `cd frontend && npx next build` (type-check + build) |
| Full suite command | `cd frontend && npx next build` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DISP-01 | Trading Plan panel renders on ticker detail page | manual-only | Manual visual verification | ❌ — no test framework |

**Justification for manual-only:** The project has zero frontend test infrastructure (no jest, vitest, playwright, or cypress config). No test files exist in `frontend/src/`. The validation for this phase relies on TypeScript compilation (`next build` type-checks) and manual visual verification.

### Sampling Rate
- **Per task commit:** `cd frontend && npx next build` (catches type errors)
- **Per wave merge:** Same
- **Phase gate:** Successful build + manual verification of all states (loaded, empty, invalid, loading)

### Wave 0 Gaps
- No test framework to set up — consistent with all prior phases
- TypeScript compilation via `next build` serves as the automated quality gate

## Security Domain

This phase has minimal security surface:

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | No | N/A — read-only display, no auth in app |
| V3 Session Management | No | N/A |
| V4 Access Control | No | N/A — public data display |
| V5 Input Validation | No | N/A — no user input, display-only |
| V6 Cryptography | No | N/A |

### Known Threat Patterns

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| XSS via reasoning text | Tampering | React auto-escapes JSX text content — no `dangerouslySetInnerHTML` needed |
| API data injection | Tampering | Type narrowing on API response + null checks before display |

**No additional security controls needed.** This is a read-only display component consuming trusted API data.

## Sources

### Primary (HIGH confidence)
- `frontend/src/components/support-resistance-card.tsx` — two-column layout, dense rows, Vietnamese formatting
- `frontend/src/components/analysis-card.tsx` — ScoreBar, SIGNAL_CONFIG, Badge patterns
- `frontend/src/lib/api.ts` — AnalysisSummary type, apiFetch pattern, ApiError handling
- `frontend/src/lib/hooks.ts` — useQuery hook patterns, staleTime conventions
- `frontend/src/app/ticker/[symbol]/page.tsx` — page layout, insertion point, conditional rendering
- `backend/app/schemas/analysis.py` — AnalysisResultResponse (lines 157-165), SummaryResponse (lines 209-216), TickerTradingSignal (lines 142-148)
- `backend/app/api/analysis.py` — trading-signal endpoint (lines 343-363), summary endpoint (lines 366-402)
- `backend/app/services/ai_analysis_service.py` — raw_response storage (line 680)
- `backend/app/models/ai_analysis.py` — raw_response JSONB column (line 51)
- `frontend/package.json` — all dependency versions verified

### Secondary (MEDIUM confidence)
- `.planning/phases/20-trading-plan-dashboard-panel/20-UI-SPEC.md` — design contract
- `.planning/phases/20-trading-plan-dashboard-panel/20-CONTEXT.md` — locked decisions

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — zero new dependencies, all versions verified from package.json and npm list
- Architecture: HIGH — all patterns verified from existing codebase, direct code inspection
- Pitfalls: HIGH — backend gap confirmed by reading AnalysisResultResponse schema vs raw_response storage
- Data flow: HIGH — backend endpoint, schema, and storage logic all verified by reading source

**Research date:** 2026-04-20
**Valid until:** 2026-05-20 (stable — no dependency changes expected)
