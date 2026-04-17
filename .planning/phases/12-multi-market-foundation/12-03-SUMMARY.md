---
phase: 12-multi-market-foundation
plan: "03"
subsystem: frontend
tags: [exchange-filter, exchange-badge, heatmap, zustand-store, css-variables, multi-exchange]
dependency_graph:
  requires: [exchange-filtered-api, exchange-field-in-responses]
  provides: [exchange-filter-component, exchange-badge-component, exchange-store, exchange-aware-hooks, exchange-css-variables]
  affects: [frontend/src/app/globals.css, frontend/src/lib/api.ts, frontend/src/lib/hooks.ts, frontend/src/lib/store.ts, frontend/src/components/exchange-filter.tsx, frontend/src/components/exchange-badge.tsx, frontend/src/app/page.tsx, frontend/src/components/heatmap.tsx]
tech_stack:
  added: []
  patterns: [zustand-persist-exchange-filter, css-custom-properties-exchange-colors, exchange-aware-query-keys]
key_files:
  created:
    - frontend/src/components/exchange-filter.tsx
    - frontend/src/components/exchange-badge.tsx
  modified:
    - frontend/src/app/globals.css
    - frontend/src/lib/api.ts
    - frontend/src/lib/hooks.ts
    - frontend/src/lib/store.ts
    - frontend/src/app/page.tsx
    - frontend/src/components/heatmap.tsx
decisions:
  - Exchange store named useExchangeStore (not useExchangeFilterStore as in UI-SPEC) for brevity — consistent with plan spec
  - Exchange type is string (not union literal) in interfaces — matches backend Pydantic str output
  - triggerOnDemandAnalysis immediately invalidates + deferred 5s invalidation for background completion
metrics:
  duration: "3m 9s"
  completed: "2026-04-17T17:59:49Z"
  tasks: 2
  tests_added: 0
  tests_total: 222
  files_changed: 8
requirements:
  - MKT-01
  - MKT-02
---

# Phase 12 Plan 03: Frontend Exchange Filter & Heatmap Integration Summary

**One-liner:** Exchange filter tabs (Tất cả/HOSE/HNX/UPCOM) with zustand persist, exchange-colored heatmap borders (blue/green/orange), ExchangeBadge component, and all supporting frontend infrastructure (CSS variables, types, hooks, store).

## What Was Built

### Task 1: Frontend Types, Store, Hooks, and CSS Variables

**CSS (globals.css):**
- Exchange CSS custom properties in `:root`: `--exchange-hose` (blue #3b82f6), `--exchange-hnx` (green #22c55e), `--exchange-upcom` (orange #f97316)
- Foreground variants for text: `--exchange-hose-fg`, `--exchange-hnx-fg`, `--exchange-upcom-fg`
- Dark mode overrides in `.dark` for foreground colors (brighter variants for contrast)

**API Types (api.ts):**
- `Ticker` interface: added `exchange: string` field
- `MarketTicker` interface: added `exchange: string` field
- `fetchTickers(sector?, exchange?)`: accepts optional exchange parameter, uses URLSearchParams
- `fetchMarketOverview(exchange?)`: accepts optional exchange filter
- `triggerOnDemandAnalysis(symbol)`: POST to `/api/analysis/{symbol}/analyze-now`

**Hooks (hooks.ts):**
- `useTickers(sector?, exchange?)`: exchange in queryKey for proper cache separation
- `useMarketOverview(exchange?)`: exchange in queryKey `["market-overview", exchange ?? "all"]`
- `useTriggerAnalysis()`: mutation hook with immediate + delayed (5s) query invalidation

**Store (store.ts):**
- `Exchange` type: `"all" | "HOSE" | "HNX" | "UPCOM"`
- `useExchangeStore`: zustand persist store (key: `holo-exchange-filter`), default `"all"`

### Task 2: ExchangeFilter, ExchangeBadge, Page & Heatmap Integration

**ExchangeFilter (exchange-filter.tsx):**
- Segmented tab bar using shadcn Tabs + base-ui primitives
- 4 tabs: Tất cả / HOSE / HNX / UPCOM
- Reads/writes `useExchangeStore` — shared across all pages via zustand persist
- Height `h-9`, text-sm font

**ExchangeBadge (exchange-badge.tsx):**
- Color-coded outline badge per exchange
- Uses CSS custom properties for border, text, and background colors
- HOSE = blue, HNX = green, UPCOM = orange

**Market Overview Page (page.tsx):**
- ExchangeFilter placed between page title and market stats grid
- Dynamic subtitle: "Bản đồ nhiệt toàn thị trường..." (all) or "Bản đồ nhiệt sàn {EX}..." (filtered)
- `useMarketOverview(exchange)` refetches on tab switch
- Exchange passed to Heatmap component

**Heatmap (heatmap.tsx):**
- Desktop tiles: `border-2` with `EXCHANGE_BORDER_COLORS` mapping (blue/green/orange)
- Mobile list: `ExchangeBadge` inline after symbol, before company name
- Enhanced empty state with exchange-specific message: "Không có mã nào trên sàn {EX}..."

## Commits

| # | Hash | Type | Description |
|---|------|------|-------------|
| 1 | `5963aa6` | feat | Exchange types, store, hooks, and CSS variables |
| 2 | `124e26c` | feat | ExchangeFilter, ExchangeBadge, market overview + heatmap integration |

## Backward Compatibility

- `useTickers()` and `useMarketOverview()` work without arguments (default `"all"` behavior)
- `fetchTickers()` and `fetchMarketOverview()` maintain backward-compatible signatures
- Heatmap renders correctly when `exchange` prop is undefined (no border class applied)
- `Ticker` and `MarketTicker` interfaces are additive (only added `exchange` field)

## Deviations from Plan

None — plan executed exactly as written.

## Threat Mitigations

| Threat ID | Disposition | Implementation |
|-----------|-------------|----------------|
| T-12-07 (Tampering: exchange store value) | accepted | Exchange type constrained to `"all" \| "HOSE" \| "HNX" \| "UPCOM"` union; backend validates allowlist (Plan 02) |
| T-12-08 (Info disclosure: localStorage persist) | accepted | `holo-exchange-filter` stores only exchange string — no PII |

## Self-Check: PASSED

All files exist, all commits verified.
