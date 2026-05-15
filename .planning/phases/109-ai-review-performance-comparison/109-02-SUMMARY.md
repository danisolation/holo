---
phase: 109
plan: 02
subsystem: frontend/simulator-review
tags: [ai-review, comparison, recharts, simulator, gemini]
dependency_graph:
  requires: [simulator_review_service, review_endpoints, comparison_endpoint]
  provides: [portfolio_review_panel, trade_review_panel, comparison_section, review_hooks]
  affects: [simulator-page-layout]
tech_stack:
  added: []
  patterns: [useMutation-for-gemini, equity-overlay-chart, metrics-comparison-table]
key_files:
  created:
    - frontend/src/components/simulator/portfolio-review-panel.tsx
    - frontend/src/components/simulator/trade-review-panel.tsx
    - frontend/src/components/simulator/comparison-section.tsx
  modified:
    - frontend/src/lib/api.ts
    - frontend/src/lib/hooks.ts
    - frontend/src/app/simulator/page.tsx
    - frontend/src/components/simulator/trade-history.tsx
decisions:
  - "useMutation for review hooks (not useQuery) — Gemini calls are expensive/on-demand"
  - "Compare tab passes 'ai' as fallback portfolioType to avoid hook error"
  - "Trade review only on SELL rows (BUY trades have no P&L data)"
  - "AI blue (#3b82f6), User amber (#f59e0b) for equity overlay lines"
metrics:
  duration: "~6 min"
  completed: "2025-05-15"
  tasks_completed: 3
  tasks_total: 3
  files_changed: 7
---

# Phase 109 Plan 02: AI Review Panels + Comparison UI Summary

Frontend UI for Gemini portfolio/trade reviews with useMutation hooks and side-by-side AI vs User equity overlay chart + metrics comparison table in new 3rd "So sánh" tab.

## Completed Tasks

| # | Task | Commit | Key Files |
|---|------|--------|-----------|
| 1 | TypeScript types, fetch functions, and hooks | `1f9e9f8` | `api.ts`, `hooks.ts` |
| 2 | Portfolio review panel + trade review panel components | `2a507c2` | `portfolio-review-panel.tsx`, `trade-review-panel.tsx` |
| 3 | Comparison section + integrate into simulator page | `61fd156` | `comparison-section.tsx`, `page.tsx`, `trade-history.tsx` |

## What Was Built

### API Layer (`frontend/src/lib/api.ts`)
- 3 new TypeScript interfaces: `PortfolioReviewResponse`, `TradeReviewResponse`, `ComparisonResponse`
- 3 fetch functions: `fetchPortfolioReview` (POST), `fetchTradeReview` (POST), `fetchComparison` (GET)

### Hooks (`frontend/src/lib/hooks.ts`)
- `usePortfolioReview(portfolioType)` — useMutation (on-demand Gemini call)
- `useTradeReview()` — useMutation with `{tradeId, portfolioType}` params
- `useComparison()` — useQuery with 60s staleTime

### Portfolio Review Panel (`portfolio-review-panel.tsx`)
- Card with "Phân tích danh mục" button that triggers Gemini analysis
- Displays: score badge (color-coded 1-10), overall assessment, strengths (green), weaknesses (amber), suggestions, risk assessment
- Loading skeleton, error state, idle prompt — all Vietnamese

### Trade Review Panel (`trade-review-panel.tsx`)
- Inline ghost button "🔍 Review" on SELL trade rows
- Expands to show: verdict badge (Tốt/Trung bình/Cần cải thiện), entry/exit analysis, what went well/could improve, pattern identified
- Disabled while pending (T-109-05 DoS mitigation)

### Comparison Section (`comparison-section.tsx`)
- **Equity Overlay Chart**: Recharts LineChart with merged date data, AI (blue #3b82f6) + User (amber #f59e0b) lines, reference line at starting capital, Vietnamese formatted tooltips
- **Portfolio Summary Cards**: Side-by-side AI vs User total equity, P&L, P&L%, position count
- **Metrics Comparison Table**: 7-row table with win rate, avg return, total P&L — better values highlighted green

### Simulator Page Integration (`page.tsx`)
- 3rd top-level tab "📊 So sánh" added alongside AI/User tabs
- PortfolioReviewPanel placed below positions in AI/User tabs
- Reset button hidden on compare tab
- `useState<"ai" | "user" | "compare">` with "ai" fallback for hook

### Trade History Integration (`trade-history.tsx`)
- New "Review" column header
- TradeReviewPanel rendered for SELL rows only, empty for BUY rows

## Deviations from Plan

None — plan executed exactly as written.

## Verification Results

- ✅ `npx tsc --noEmit` — zero TypeScript errors
- ✅ `npm run build` — production build succeeds (11/11 pages)
- ✅ 3 top-level tabs: AI Portfolio, Danh mục thủ công, So sánh
- ✅ PortfolioReviewPanel renders in both AI and User tabs
- ✅ SELL trade rows have Review button, BUY rows don't
- ✅ ComparisonSection with equity overlay + metrics table
- ✅ All labels in Vietnamese

## Self-Check: PASSED
