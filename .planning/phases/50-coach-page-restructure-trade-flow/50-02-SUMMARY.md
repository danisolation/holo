---
phase: 50-coach-page-restructure-trade-flow
plan: "02"
subsystem: frontend/app/coach
tags: [tab-layout, trade-flow, coach-page, restructure, ux]
dependency_graph:
  requires:
    - TradePrefill interface from Plan 01
    - onRecordTrade callback on PickCard from Plan 01
    - PostTradeCard component from Plan 01
  provides:
    - Tab-based Coach page layout (Picks / Nhật ký / Mục tiêu)
    - Complete trade recording flow wired end-to-end
  affects:
    - frontend/src/app/coach/page.tsx
tech_stack:
  added: []
  patterns:
    - Controlled Tabs with base-ui onValueChange for programmatic tab switching
    - Trade flow state machine: pick → prefill dialog → post-trade card → journal tab
    - Conditional PostTradeCard rendering tied to lastTradeData state
key_files:
  created: []
  modified:
    - frontend/src/app/coach/page.tsx
decisions:
  - "Tab values use simple strings (picks/journal/goals) for readability"
  - "PostTradeCard renders at top of Picks tab for immediate visibility after trade"
  - "handleViewJournal clears post-trade state then switches tab to avoid stale card on return"
metrics:
  duration: 3m
  completed: 2026-04-24T07:53:00Z
  tasks_completed: 1
  tasks_total: 1
  files_changed: 1
---

# Phase 50 Plan 02: Coach Page Tab Layout & Trade Flow Wiring Summary

**One-liner:** Coach page restructured from single-scroll to 3-tab layout (Picks/Nhật ký/Mục tiêu) with end-to-end trade flow: PickCard → prefilled TradeEntryDialog → PostTradeCard → journal tab switch.

## Tasks Completed

| # | Task | Commit | Key Changes |
|---|------|--------|-------------|
| 1 | Restructure coach/page.tsx with tab-based layout and wire the complete trade flow | `669e538` | Replaced scroll layout with Tabs, added trade dialog/prefill state, PostTradeCard rendering, handleViewJournal tab switch |

## What Was Built

### Tab-Based Layout
- **Three tabs**: Picks (default), Nhật ký (journal), Mục tiêu (goals)
- **Controlled state**: `activeTab` managed via `useState`, enabling programmatic switching via `setActiveTab`
- **Content organization**: Performance cards + pick grid + almost-selected in Picks tab; open trades + pick history + behavior insights in Nhật ký tab; monthly goal + weekly prompt + weekly review in Mục tiêu tab

### Trade Recording Flow (End-to-End Wiring)
- **PickCard → Dialog**: `handleRecordTrade` builds `TradePrefill` from `DailyPickResponse` (ticker, entry price, position size, daily_pick_id, SL/TP) and opens `TradeEntryDialog`
- **Dialog → PostTradeCard**: `handleTradeCreated` receives `TradeResponse`, matches it with the source pick, stores both in `lastTradeData` state
- **PostTradeCard rendering**: Appears at top of Picks tab showing trade summary, SL/TP monitoring levels, and next-step guidance
- **Journal navigation**: `handleViewJournal` clears post-trade state and switches to journal tab via `setActiveTab("journal")`
- **Dismiss**: `handleDismissPostTrade` clears `lastTradeData` to remove the card

### Preserved Functionality
- All existing sections maintained in their respective tabs
- Delete trade dialog and handlers preserved
- Risk suggestion banner remains global (above tabs)
- Profile settings card remains in header

## Deviations from Plan

None — plan executed exactly as written.

## Verification

- TypeScript compilation: `npx tsc --noEmit` passes with zero errors
- Next.js build: `npm run build` passes clean
- All 13 acceptance criteria checks pass (TabsTrigger, tab values, Vietnamese labels, wiring props, PostTradeCard, controlled tabs)

## Self-Check: PASSED

- ✅ frontend/src/app/coach/page.tsx exists
- ✅ 50-02-SUMMARY.md exists
- ✅ Commit 669e538 verified in git log
