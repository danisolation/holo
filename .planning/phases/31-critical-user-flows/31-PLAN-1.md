---
phase: 31
plan: 1
type: test
wave: 1
depends_on: []
files_modified:
  - frontend/e2e/flow-ticker-to-trade.spec.ts
  - frontend/e2e/flow-paper-trading-dashboard.spec.ts
  - frontend/e2e/flow-watchlist.spec.ts
  - frontend/e2e/flow-settings.spec.ts
autonomous: true
requirements: [FLOW-01, FLOW-02, FLOW-03, FLOW-04]
---

# Plan 31.1: Critical User Flow Tests

<objective>
Create multi-page end-to-end tests simulating real user journeys: ticker→analysis→trade, paper trading dashboard exploration, watchlist management, and settings persistence.
</objective>

<tasks>

<task id="1" type="file">
<title>Create ticker-to-trade flow test</title>
<read_first>
- frontend/src/app/ticker/[symbol]/page.tsx (page structure, analysis sections, trading plan)
- frontend/src/components/trading-plan-panel.tsx (Follow button, ManualFollow functionality)
- frontend/e2e/fixtures/api-helpers.ts (API helpers)
- frontend/e2e/fixtures/test-helpers.ts (TEST_TICKER constant)
</read_first>
<action>
Create `frontend/e2e/flow-ticker-to-trade.spec.ts`:

Test FLOW-01: Open ticker → view analysis → view trading plan → click Follow → verify paper trade created.

Flow:
1. Navigate to `/ticker/VNM`
2. Verify ticker page loads (`[data-testid="ticker-page"]`)
3. Verify chart renders (`[data-testid="ticker-chart"]`)
4. Scroll to analysis section (`[data-testid="ticker-analysis"]`) — verify visible
5. Look for trading plan panel / Follow button
6. If Follow button exists: click it and verify success state (button changes to check icon or success message)
7. Navigate to `/dashboard/paper-trading` to verify trade appears in trades list
8. If no Follow button (no trading signal available): skip trade creation, verify page structure only

Handle gracefully: trading signals may not exist for the test ticker. The test should pass whether or not a Follow action is available, but must verify page navigation works end-to-end.
</action>
<verify>
`frontend/e2e/flow-ticker-to-trade.spec.ts` exists with multi-page flow
</verify>
<acceptance_criteria>
- File navigates from `/ticker/VNM` to `/dashboard/paper-trading`
- File checks `[data-testid="ticker-page"]` and `[data-testid="ticker-chart"]`
- File attempts to find and interact with trading plan / Follow button
- File handles case where Follow button may not exist
</acceptance_criteria>
</task>

<task id="2" type="file">
<title>Create paper trading dashboard flow test</title>
<read_first>
- frontend/src/app/dashboard/paper-trading/page.tsx (all tabs and content)
- frontend/src/components/paper-trading/pt-trades-table.tsx (table structure)
</read_first>
<action>
Create `frontend/e2e/flow-paper-trading-dashboard.spec.ts`:

Test FLOW-02: Open paper trading dashboard → view trades → sort/filter → analytics tab → calendar tab.

Flow:
1. Navigate to `/dashboard/paper-trading`
2. Verify Overview tab content loads
3. Click Trades tab (`[data-testid="pt-tab-trades"]`)
4. Verify trades table loads (`[data-testid="pt-trades-table"]`)
5. If table has data: attempt sort by clicking a column header
6. Click Analytics tab (`[data-testid="pt-tab-analytics"]`)
7. Verify analytics content loads (`[data-testid="pt-analytics-content"]`)
8. Click Calendar tab (`[data-testid="pt-tab-calendar"]`)
9. Verify calendar content renders

This is a continuous exploration flow — user browses all tabs in sequence.
</action>
<verify>
`frontend/e2e/flow-paper-trading-dashboard.spec.ts` exists with dashboard flow
</verify>
<acceptance_criteria>
- File navigates through overview → trades → analytics → calendar tabs in sequence
- File uses `[data-testid="pt-tab-*"]` selectors
- File verifies content loads at each step
</acceptance_criteria>
</task>

<task id="3" type="file">
<title>Create watchlist management flow test</title>
<read_first>
- frontend/src/app/watchlist/page.tsx (watchlist page, add/remove mechanism)
- frontend/src/lib/hooks.ts (useWatchlist, useAddToWatchlist, useRemoveFromWatchlist)
- frontend/src/lib/api.ts (watchlist API functions)
</read_first>
<action>
Create `frontend/e2e/flow-watchlist.spec.ts`:

Test FLOW-03: Add ticker to watchlist → verify on watchlist page → remove → verify removal.

Flow:
1. Navigate to `/watchlist`
2. Verify watchlist page loads (`[data-testid="watchlist-page"]`)
3. Note initial state (number of items)
4. Add a ticker (via UI mechanism — search/add button, or via API: POST to watchlist)
5. Verify the ticker appears in the watchlist
6. Reload page → verify ticker is still there (persistence)
7. Remove the ticker (via remove button or API)
8. Verify the ticker is gone from the list

If the UI add mechanism is complex, use API helpers to add via `request.post()` and verify through UI.
</action>
<verify>
`frontend/e2e/flow-watchlist.spec.ts` exists with watchlist flow
</verify>
<acceptance_criteria>
- File tests add → verify → persist → remove → verify removal flow
- File uses `/watchlist` page
- File includes persistence check (page.reload or re-navigation)
</acceptance_criteria>
</task>

<task id="4" type="file">
<title>Create settings persistence flow test</title>
<read_first>
- frontend/src/components/paper-trading/pt-settings-form.tsx (form structure)
- frontend/src/app/dashboard/paper-trading/page.tsx (overview tab content that shows settings-derived info)
</read_first>
<action>
Create `frontend/e2e/flow-settings.spec.ts`:

Test FLOW-04: Change paper trading settings → verify persist → verify affects overview.

Flow:
1. Navigate to `/dashboard/paper-trading`
2. Click Settings tab
3. Read current form values
4. Modify a setting (e.g., initial capital)
5. Submit the form
6. Verify success
7. Reload page → verify settings tab shows updated value
8. Click Overview tab → verify overview reflects the change (e.g., capital display)

If overview doesn't directly show setting values, verify the settings API returns the updated value instead.
</action>
<verify>
`frontend/e2e/flow-settings.spec.ts` exists with settings flow
</verify>
<acceptance_criteria>
- File modifies a paper trading setting
- File submits the form
- File verifies persistence after reload
- File checks overview tab or API for effect of settings change
</acceptance_criteria>
</task>

</tasks>

<verification>
1. `npx playwright test --list` shows all 4 flow test files
2. Each test navigates across multiple pages/tabs
3. Tests handle empty states gracefully
4. No specific data value assertions
</verification>

<success_criteria>
Addresses FLOW-01 through FLOW-04.
</success_criteria>

<must_haves>
- Ticker → analysis → trade creation flow
- Paper trading dashboard multi-tab exploration flow
- Watchlist add → persist → remove → verify flow
- Settings change → persist → effect verification flow
</must_haves>
