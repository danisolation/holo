---
phase: 17-enhanced-technical-indicators
plan: "02"
title: "Frontend (Accordion + chart components + type extension)"
subsystem: frontend
tags: [charts, accordion, lightweight-charts, indicators, typescript]
dependency_graph:
  requires: []
  provides:
    - "shadcn Accordion component (base-nova / @base-ui/react)"
    - "ATRChart, ADXChart, StochasticChart components"
    - "IndicatorData type with 18 fields (12 existing + 6 new)"
  affects:
    - "frontend/src/components/indicator-chart.tsx"
    - "frontend/src/lib/api.ts"
tech_stack:
  added: ["@base-ui/react/accordion (via shadcn)"]
  patterns: ["Accordion multiple with defaultValue for chart visibility"]
key_files:
  created:
    - "frontend/src/components/ui/accordion.tsx"
  modified:
    - "frontend/src/lib/api.ts"
    - "frontend/src/components/indicator-chart.tsx"
decisions:
  - "Used base-ui `multiple` prop instead of radix-style `type=\"multiple\"` (library adaptation)"
  - "Moved h4 labels from inside chart components to AccordionTrigger for proper accordion UX"
metrics:
  duration: "3.2m"
  tasks_completed: 2
  tasks_total: 2
  files_created: 1
  files_modified: 2
  completed_date: "2026-04-20"
---

# Phase 17 Plan 02: Frontend (Accordion + chart components + type extension) Summary

ATR/ADX/Stochastic sub-chart components with collapsible Accordion wrapper using base-ui, extending IndicatorData with 6 nullable fields for volatility/trend/momentum display.

## Completed Tasks

| # | Task | Commit | Key Changes |
|---|------|--------|-------------|
| 1 | Install shadcn Accordion + extend IndicatorData type | `16358af` | Added accordion.tsx, 6 new fields in IndicatorData |
| 2 | Add ATRChart, ADXChart, StochasticChart + Accordion wrapper | `02d6aec` | 3 new chart components, Accordion wrapping all 5 charts |

## Implementation Details

### shadcn Accordion (Task 1)
- Installed via `npx shadcn@latest add accordion --yes` using base-nova style
- Component uses `@base-ui/react/accordion` primitives (not Radix)
- Exports: `Accordion`, `AccordionItem`, `AccordionTrigger`, `AccordionContent`

### IndicatorData Extension (Task 1)
- Added 6 nullable number fields: `atr_14`, `adx_14`, `plus_di_14`, `minus_di_14`, `stoch_k_14`, `stoch_d_14`
- Field names match backend API response keys exactly

### New Chart Components (Task 2)
- **ATRChart**: Single amber (#FBBF24) line, lineWidth 2, lastValueVisible
- **ADXChart**: Cyan (#06B6D4) ADX + green (#22C55E) +DI + red (#EF4444) -DI + dashed white ref at 25
- **StochasticChart**: Pink (#EC4899) %K + indigo (#818CF8) %D + dashed 80/20 overbought/oversold zones
- All follow existing RSIChart pattern: useRef + useEffect + createChart(160px) + ResizeObserver cleanup

### Accordion Integration (Task 2)
- All 5 charts (RSI, MACD, ATR, ADX, Stochastic) wrapped in `<Accordion multiple defaultValue={["rsi", "macd"]}>`
- RSI and MACD expanded by default (preserving existing behavior)
- ATR, ADX, Stochastic collapsed by default (new, opt-in)
- Labels moved from internal h4 to AccordionTrigger with inline color legends

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Adapted Accordion API from radix to base-ui**
- **Found during:** Task 2
- **Issue:** Plan specified `type="multiple"` (radix-style) but installed shadcn uses @base-ui/react which has `multiple` boolean prop
- **Fix:** Used `<Accordion multiple defaultValue={["rsi", "macd"]}>` instead of `<Accordion type="multiple" defaultValue={["rsi", "macd"]}>`
- **Files modified:** frontend/src/components/indicator-chart.tsx
- **Commit:** 02d6aec

## Verification

- ✅ `frontend/src/components/ui/accordion.tsx` exists with AccordionTrigger + AccordionContent exports
- ✅ `IndicatorData` has 18 fields (12 existing + 6 new nullable number fields)
- ✅ ATRChart, ADXChart, StochasticChart functions defined
- ✅ 5 AccordionItem entries wrapping all charts
- ✅ Correct colors: ATR amber, ADX cyan, +DI green, -DI red, %K pink, %D indigo
- ✅ Reference lines: ADX at 25, Stochastic at 80/20
- ✅ Vietnamese labels: "Biến động giá", "quá mua", "quá bán", "xu hướng mạnh"
- ✅ Next.js build compiles with zero errors

## Self-Check: PASSED

All 4 files verified on disk. Both commit hashes (16358af, 02d6aec) found in git log.
