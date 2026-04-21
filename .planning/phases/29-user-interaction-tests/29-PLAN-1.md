---
phase: 29
plan: 1
type: test
wave: 1
depends_on: []
files_modified:
  - frontend/e2e/interact-pt-settings.spec.ts
  - frontend/e2e/interact-pt-tabs.spec.ts
  - frontend/e2e/interact-trades-table.spec.ts
  - frontend/e2e/interact-watchlist.spec.ts
  - frontend/e2e/interact-ticker.spec.ts
autonomous: true
requirements: [INTERACT-01, INTERACT-02, INTERACT-03, INTERACT-04, INTERACT-05]
---

# Plan 29.1: User Interaction Tests

<objective>
Write Playwright tests verifying forms submit and persist, tables sort and filter correctly, tabs switch content, watchlist add/remove persists, and ticker detail controls work.
</objective>

<tasks>

<task id="1" type="file">
<title>Create paper trading settings form test</title>
<read_first>
- frontend/src/components/paper-trading/pt-settings-form.tsx (form fields, submit button, current form structure)
- frontend/e2e/fixtures/api-helpers.ts (getPaperSettings method)
- frontend/e2e/fixtures/test-helpers.ts (navigateAndWait)
</read_first>
<action>
Create `frontend/e2e/interact-pt-settings.spec.ts`:

Test INTERACT-01: Paper trading settings form submits successfully and values persist through page reload.

Test structure:
1. Navigate to `/dashboard/paper-trading`
2. Click settings tab (`[data-testid="pt-tab-settings"]`)
3. Wait for settings form to be visible (`[data-testid="pt-settings-form"]`)
4. Fill or modify a form field (e.g., initial capital)
5. Click submit button (`[data-testid="pt-settings-submit"]`)
6. Wait for success indication (toast, button state change, or API response)
7. Reload the page
8. Navigate back to settings tab
9. Verify the form shows the submitted value

Use structure-based assertions — verify form submission succeeds and value persists, but don't assert specific default values.
</action>
<verify>
`frontend/e2e/interact-pt-settings.spec.ts` exists with form submit and persistence test
</verify>
<acceptance_criteria>
- File contains test that clicks `[data-testid="pt-tab-settings"]`
- File contains interaction with `[data-testid="pt-settings-form"]`
- File contains `page.reload()` to verify persistence
- File contains assertion after reload
</acceptance_criteria>
</task>

<task id="2" type="file">
<title>Create paper trading tab switching test</title>
<read_first>
- frontend/src/app/dashboard/paper-trading/page.tsx (tab structure, all TabsTrigger/TabsContent values)
</read_first>
<action>
Create `frontend/e2e/interact-pt-tabs.spec.ts`:

Test INTERACT-04: Tab switching on paper trading dashboard renders correct content for each tab.

Test structure:
1. Navigate to `/dashboard/paper-trading`
2. Verify Overview tab is active by default (content visible)
3. Click Trades tab → verify trades content appears (`[data-testid="pt-trades-table"]` or trades-specific content)
4. Click Analytics tab → verify analytics content appears (`[data-testid="pt-analytics-content"]`)
5. Click Calendar tab → verify calendar content appears
6. Click Settings tab → verify settings form appears (`[data-testid="pt-settings-form"]`)
7. Click back to Overview → verify overview content returns

Each tab click should show the corresponding content and hide the others.
</action>
<verify>
`frontend/e2e/interact-pt-tabs.spec.ts` exists with tab switching tests
</verify>
<acceptance_criteria>
- File contains clicks on all 5 tabs (overview, trades, analytics, calendar, settings)
- File uses `[data-testid="pt-tab-*"]` selectors for clicking
- File verifies content changes after each tab click
</acceptance_criteria>
</task>

<task id="3" type="file">
<title>Create trades table sorting/filtering test</title>
<read_first>
- frontend/src/components/paper-trading/pt-trades-table.tsx (table structure, sortable columns, filter controls)
</read_first>
<action>
Create `frontend/e2e/interact-trades-table.spec.ts`:

Test INTERACT-02: Trade table sorting and filtering work correctly.

Test structure:
1. Navigate to `/dashboard/paper-trading`
2. Click Trades tab
3. Wait for trades table to be visible (`[data-testid="pt-trades-table"]`)
4. If table has data rows:
   - Click a column header (e.g., date, P&L, status) to sort
   - Verify the sort indication changes (arrow direction, active state)
   - Click again to reverse sort
5. If filter controls exist:
   - Click a filter (direction or status dropdown/buttons)
   - Verify table content changes (row count may change)
6. If table is empty, verify empty state message is shown

Note: Don't assert specific row values — data is live. Assert on sort indicators and row count changes.
</action>
<verify>
`frontend/e2e/interact-trades-table.spec.ts` exists with sorting/filtering tests
</verify>
<acceptance_criteria>
- File navigates to trades tab
- File interacts with table headers or sort controls
- File checks for sort indicators or content changes
</acceptance_criteria>
</task>

<task id="4" type="file">
<title>Create watchlist interaction test</title>
<read_first>
- frontend/src/app/watchlist/page.tsx (watchlist page structure, add/remove UI)
- frontend/src/components/ticker-search.tsx (search component for adding tickers)
- frontend/src/lib/hooks.ts (useWatchlist, useAddToWatchlist, useRemoveFromWatchlist hooks)
- frontend/src/lib/api.ts (watchlist API functions)
</read_first>
<action>
Create `frontend/e2e/interact-watchlist.spec.ts`:

Test INTERACT-03: Watchlist add/remove ticker works and persists across page reload.

Test structure:
1. Navigate to `/watchlist`
2. Note current watchlist state (count of items)
3. Use the ticker search or add mechanism to add a ticker (e.g., "VNM")
4. Verify the ticker appears in the watchlist table
5. Reload the page
6. Verify the ticker is still in the watchlist (persistence)
7. Remove the ticker via remove button/action
8. Verify the ticker is removed from the list

If the add/remove mechanism uses API calls, use the ApiHelpers to verify state.
Adapt the test to the actual UI mechanism found in the code.
</action>
<verify>
`frontend/e2e/interact-watchlist.spec.ts` exists with add/remove/persist tests
</verify>
<acceptance_criteria>
- File navigates to `/watchlist`
- File performs an add or verify action
- File contains `page.reload()` for persistence check
- File verifies removal or state change
</acceptance_criteria>
</task>

<task id="5" type="file">
<title>Create ticker detail interaction test</title>
<read_first>
- frontend/src/app/ticker/[symbol]/page.tsx (ticker page structure, tabs, chart controls)
</read_first>
<action>
Create `frontend/e2e/interact-ticker.spec.ts`:

Test INTERACT-05: Ticker detail page tabs and interactive chart controls work.

Test structure:
1. Navigate to `/ticker/VNM`
2. Verify page loads with ticker page content (`[data-testid="ticker-page"]`)
3. Verify chart container is visible (`[data-testid="ticker-chart"]`)
4. If tabs exist on ticker page:
   - Click each tab and verify content changes
5. If chart has controls (timeframe buttons like 1D, 1W, 1M, etc.):
   - Click different timeframe options
   - Verify chart container is still visible (didn't break)
6. If analysis section exists (`[data-testid="ticker-analysis"]`):
   - Verify it renders content

Don't assert specific chart data or prices — just verify controls respond and page doesn't break.
</action>
<verify>
`frontend/e2e/interact-ticker.spec.ts` exists with ticker interaction tests
</verify>
<acceptance_criteria>
- File navigates to `/ticker/VNM` (or TEST_TICKER)
- File checks `[data-testid="ticker-page"]` visibility
- File checks `[data-testid="ticker-chart"]` visibility
- File interacts with tabs or controls on the page
</acceptance_criteria>
</task>

</tasks>

<verification>
1. `npx playwright test --list` shows all 5 interaction test files
2. Tests use data-testid selectors from Phase 27
3. Persistence tests include page.reload()
4. No specific data value assertions
</verification>

<success_criteria>
Addresses INTERACT-01 through INTERACT-05.
</success_criteria>

<must_haves>
- Settings form submit + persistence via reload
- Tab switching across all 5 PT tabs
- Trade table sort/filter interaction
- Watchlist add/remove with persistence
- Ticker detail page tab/chart control interaction
</must_haves>
