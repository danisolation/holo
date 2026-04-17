---
status: awaiting_human_verify
trigger: "Candlestick chart SMA overlay crashes with 'data must be asc ordered by time' assertion error when rendering on ticker detail pages."
created: 2025-01-27T12:00:00Z
updated: 2025-01-27T12:00:00Z
---

## Current Focus

hypothesis: Backend indicators endpoint returns data in descending order (newest first) while lightweight-charts requires ascending (oldest first)
test: Checked backend query ordering vs chart library requirements
expecting: Mismatch between query ORDER BY and chart setData requirement
next_action: Fix backend to return indicators in ascending date order

## Symptoms

expected: Candlestick chart with SMA lines (SMA20, SMA50 etc.) should render without errors on ticker detail pages.
actual: Assertion failure: "data must be asc ordered by time, index=1, time=1776211200, prev time=1776297600". The SMA20 setData call at line 130 of candlestick-chart.tsx triggers the error. The prev time (1776297600) is GREATER than the current time (1776211200), meaning the data array is sorted in descending order (newest first) instead of ascending order (oldest first).
errors: Assertion failed: data must be asc ordered by time, index=1, time=1776211200, prev time=1776297600
reproduction: Open any ticker detail page (e.g., /ticker/VNM). The chart immediately crashes.
started: Never worked — first time testing this feature.

## Eliminated

(none)

## Evidence

- timestamp: 2025-01-27T12:00:00Z
  checked: backend/app/api/tickers.py — prices endpoint
  found: Line 92 uses `.order_by(DailyPrice.date.asc())` — correctly ascending
  implication: Price/candlestick data is correctly sorted. The crash is NOT from candlestick data.

- timestamp: 2025-01-27T12:01:00Z
  checked: backend/app/api/analysis.py — indicators endpoint (line 148-153)
  found: Line 151 uses `.order_by(TechnicalIndicator.date.desc())` — DESCENDING (newest first)
  implication: This is the root cause. Indicator data (SMA, BB, RSI, MACD) arrives at frontend in reverse chronological order.

- timestamp: 2025-01-27T12:02:00Z
  checked: frontend/src/components/candlestick-chart.tsx — data handling
  found: filteredIndicators is used directly without sorting. SMA/BB data arrays inherit the descending order from the API response.
  implication: setData() receives descending data → lightweight-charts assertion fails.

- timestamp: 2025-01-27T12:03:00Z
  checked: frontend/src/components/indicator-chart.tsx — RSI and MACD charts
  found: Same pattern — indicatorData used directly without sorting. Also passes descending data to setData().
  implication: indicator-chart.tsx has the same latent bug (would also crash if rendered).

## Resolution

root_cause: Backend `GET /api/analysis/{symbol}/indicators` orders results by `TechnicalIndicator.date.desc()` (descending) to get the most recent N records, but returns them in that descending order. The lightweight-charts library requires all setData() arrays to be sorted ascending by time. The prices endpoint correctly uses `.asc()` but the indicators endpoint uses `.desc()` without reversing.
fix: Reverse the indicator rows list before building the response, so data returns in ascending chronological order (oldest first) — matching what lightweight-charts requires.
verification: Fix applied — reversed indicator rows before returning response. The query still uses DESC+LIMIT to get the latest N records, then reverses to ascending order for the response. This matches the pattern of the prices endpoint which uses .asc() directly.
files_changed:
  - backend/app/api/analysis.py
