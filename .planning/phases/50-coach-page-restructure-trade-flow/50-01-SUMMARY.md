---
phase: 50-coach-page-restructure-trade-flow
plan: "01"
subsystem: frontend/components
tags: [trade-flow, prefill, pick-card, post-trade, ui-components]
dependency_graph:
  requires: []
  provides:
    - TradePrefill interface for pre-filling TradeEntryDialog from picks
    - onRecordTrade callback on PickCard for triggering trade recording
    - PostTradeCard component for post-trade guidance
  affects:
    - frontend/src/components/trade-entry-dialog.tsx
    - frontend/src/components/pick-card.tsx
    - frontend/src/components/post-trade-card.tsx
tech_stack:
  added: []
  patterns:
    - Conditional readonly display vs interactive input based on prefill prop
    - stopPropagation for nested button in clickable card
    - Dynamic numbered next-step guidance from nullable SL/TP values
key_files:
  created:
    - frontend/src/components/post-trade-card.tsx
  modified:
    - frontend/src/components/trade-entry-dialog.tsx
    - frontend/src/components/pick-card.tsx
decisions:
  - "TradePrefill carries stop_loss/take_profit_1 for PostTradeCard usage downstream"
  - "Readonly ticker display with Badge when prefill active — user edits price/quantity but not ticker"
  - "onTradeCreated called after dialog close to allow parent to transition state"
metrics:
  duration: 4m
  completed: 2026-04-24T14:47:00Z
  tasks_completed: 2
  tasks_total: 2
  files_changed: 3
---

# Phase 50 Plan 01: Trade Flow Components Summary

**One-liner:** TradeEntryDialog prefill from AI picks with readonly ticker badge, PickCard "Ghi nhận giao dịch" button with stopPropagation, PostTradeCard with SL/TP monitoring and Vietnamese next-step guidance.

## Tasks Completed

| # | Task | Commit | Key Changes |
|---|------|--------|-------------|
| 1 | Extend TradeEntryDialog with prefill support and onTradeCreated callback | `fb07e01` | Added TradePrefill interface, prefill/onTradeCreated props, readonly ticker display with "Từ gợi ý AI" badge, conditional dialog title |
| 2 | Add "Ghi nhận giao dịch" button to PickCard + create PostTradeCard | `49d5f97` | Added onRecordTrade prop + button to PickCard, created PostTradeCard with trade summary, SL/TP levels, numbered next steps |

## What Was Built

### TradeEntryDialog Extensions
- **TradePrefill interface**: Exported type carrying ticker_symbol, ticker_name, price, quantity, daily_pick_id, stop_loss, take_profit_1
- **Prefill behavior**: When `prefill` prop provided, form opens pre-populated with pick data; ticker shown as readonly with "Từ gợi ý AI" badge
- **onTradeCreated callback**: Called with TradeResponse after successful mutation, enabling parent to transition to post-trade state
- **Dialog title**: Changes to "Ghi nhận giao dịch từ gợi ý" when prefill is active
- **Backward compatible**: Original behavior unchanged when no prefill provided

### PickCard Button
- **"Ghi nhận giao dịch" button**: Conditionally rendered when `onRecordTrade` prop provided
- **stopPropagation**: Prevents card-level click handler (behavior tracking) from firing
- **Callback passes full pick**: `onRecordTrade(pick)` gives parent all DailyPickResponse data

### PostTradeCard Component
- **Trade confirmation header**: Green checkmark with "Đã ghi nhận giao dịch"
- **Trade summary**: MUA badge, ticker, quantity × price = total
- **SL/TP monitoring section**: Conditionally shows stop loss (red) and take profit levels (green)
- **Next steps guidance**: Dynamically numbered Vietnamese instructions based on available SL/TP
- **Actions**: Dismiss (X button) and "Xem nhật ký giao dịch" navigation button

## Deviations from Plan

None — plan executed exactly as written.

## Verification

- TypeScript compilation: `npx tsc --noEmit` passes with zero errors
- All acceptance criteria checks pass for both tasks

## Self-Check: PASSED

All 3 source files exist, SUMMARY.md created, both commits (fb07e01, 49d5f97) verified in git log.
