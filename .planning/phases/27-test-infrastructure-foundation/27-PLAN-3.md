---
phase: 27
plan: 3
type: frontend
wave: 2
depends_on: [1]
files_modified:
  - frontend/src/components/navbar.tsx
  - frontend/src/app/dashboard/paper-trading/page.tsx
  - frontend/src/components/paper-trading/pt-settings-tab.tsx
  - frontend/src/components/paper-trading/pt-trades-tab.tsx
  - frontend/src/components/paper-trading/pt-analytics-tab.tsx
  - frontend/src/app/watchlist/page.tsx
  - frontend/src/app/ticker/[symbol]/page.tsx
autonomous: true
requirements: [INFRA-03]
---

# Plan 27.3: Add data-testid Attributes to Key Components

<objective>
Add stable `data-testid` attributes to key UI components (navbar, tabs, forms, tables, chart containers) so Playwright tests can reliably select elements without depending on CSS classes or text content.
</objective>

<tasks>

<task id="1" type="file">
<title>Add data-testid to Navbar component</title>
<read_first>
- frontend/src/components/navbar.tsx (full file — nav structure, links, theme toggle)
</read_first>
<action>
In `frontend/src/components/navbar.tsx`:

1. Add `data-testid="navbar"` to the `<header>` element
2. Add `data-testid="nav-desktop"` to the desktop `<nav>` element
3. Add `data-testid={`nav-link-${link.href.replace(/\//g, '-').replace(/^-/, '')}`}` to each nav Link (or simpler: add to the nav container)
4. Add `data-testid="theme-toggle"` to the theme toggle Button
5. Add `data-testid="ticker-search"` to the TickerSearch wrapper div
6. Add `data-testid="mobile-menu"` to the Sheet (mobile hamburger)

Example for header:
```tsx
<header data-testid="navbar" className="sticky top-0 ...">
```

Example for theme toggle button:
```tsx
<Button data-testid="theme-toggle" variant="ghost" ...>
```
</action>
<verify>
`frontend/src/components/navbar.tsx` contains `data-testid="navbar"` and `data-testid="theme-toggle"`
</verify>
<acceptance_criteria>
- `navbar.tsx` contains `data-testid="navbar"`
- `navbar.tsx` contains `data-testid="theme-toggle"`
- `navbar.tsx` contains `data-testid="nav-desktop"`
</acceptance_criteria>
</task>

<task id="2" type="file">
<title>Add data-testid to Paper Trading dashboard tabs</title>
<read_first>
- frontend/src/app/dashboard/paper-trading/page.tsx (tab structure, TabsTrigger usage)
</read_first>
<action>
In `frontend/src/app/dashboard/paper-trading/page.tsx`:

1. Add `data-testid="pt-tabs"` to the Tabs root element
2. Add `data-testid="pt-tab-{name}"` to each TabsTrigger (overview, trades, analytics, calendar, settings)
3. Add `data-testid="pt-content-{name}"` to each TabsContent

Example:
```tsx
<Tabs data-testid="pt-tabs" ...>
  <TabsTrigger data-testid="pt-tab-overview" value="overview">...</TabsTrigger>
  <TabsTrigger data-testid="pt-tab-trades" value="trades">...</TabsTrigger>
  ...
  <TabsContent data-testid="pt-content-overview" value="overview">...</TabsContent>
```
</action>
<verify>
`paper-trading/page.tsx` contains `data-testid="pt-tabs"` and `data-testid="pt-tab-overview"`
</verify>
<acceptance_criteria>
- `paper-trading/page.tsx` contains `data-testid="pt-tabs"`
- `paper-trading/page.tsx` contains `data-testid="pt-tab-overview"`
- `paper-trading/page.tsx` contains `data-testid="pt-tab-trades"`
- `paper-trading/page.tsx` contains `data-testid="pt-tab-analytics"`
- `paper-trading/page.tsx` contains `data-testid="pt-tab-settings"`
</acceptance_criteria>
</task>

<task id="3" type="file">
<title>Add data-testid to Paper Trading sub-components</title>
<read_first>
- frontend/src/components/paper-trading/pt-settings-tab.tsx (form elements)
- frontend/src/components/paper-trading/pt-trades-tab.tsx (table, filters)
- frontend/src/components/paper-trading/pt-analytics-tab.tsx (charts, stats)
</read_first>
<action>
In `pt-settings-tab.tsx`:
- Add `data-testid="pt-settings-form"` to the form wrapper
- Add `data-testid="pt-settings-submit"` to the submit button

In `pt-trades-tab.tsx`:
- Add `data-testid="pt-trades-table"` to the table wrapper/container
- Add `data-testid="pt-trades-filter"` to any filter controls

In `pt-analytics-tab.tsx`:
- Add `data-testid="pt-analytics-content"` to the main content wrapper
</action>
<verify>
Files contain the expected data-testid attributes
</verify>
<acceptance_criteria>
- `pt-settings-tab.tsx` contains `data-testid="pt-settings-form"` or `data-testid="pt-settings-submit"`
- `pt-trades-tab.tsx` contains `data-testid="pt-trades-table"`
- `pt-analytics-tab.tsx` contains `data-testid="pt-analytics-content"`
</acceptance_criteria>
</task>

<task id="4" type="file">
<title>Add data-testid to Watchlist and Ticker pages</title>
<read_first>
- frontend/src/app/watchlist/page.tsx (watchlist table, add/remove UI)
- frontend/src/app/ticker/[symbol]/page.tsx (chart container, tabs, analysis sections)
</read_first>
<action>
In `frontend/src/app/watchlist/page.tsx`:
- Add `data-testid="watchlist-page"` to the page wrapper
- Add `data-testid="watchlist-table"` to the data table wrapper

In `frontend/src/app/ticker/[symbol]/page.tsx`:
- Add `data-testid="ticker-page"` to the page wrapper
- Add `data-testid="ticker-chart"` to the chart container div
- Add `data-testid="ticker-analysis"` to the analysis section
</action>
<verify>
Files contain the expected data-testid attributes
</verify>
<acceptance_criteria>
- `watchlist/page.tsx` contains `data-testid="watchlist-page"`
- `ticker/[symbol]/page.tsx` contains `data-testid="ticker-page"`
- `ticker/[symbol]/page.tsx` contains `data-testid="ticker-chart"`
</acceptance_criteria>
</task>

</tasks>

<verification>
1. `grep -r "data-testid" frontend/src/ | wc -l` returns 15+ matches
2. Navbar, PT tabs, trades table, settings form, watchlist, ticker page all have testids
3. Frontend builds clean: `cd frontend && npm run build`
</verification>

<success_criteria>
Addresses INFRA-03: Key UI components have stable data-testid attributes for reliable Playwright selection.
</success_criteria>

<must_haves>
- data-testid on navbar element
- data-testid on paper trading tabs (each TabsTrigger)
- data-testid on paper trading table, form, analytics
- data-testid on watchlist page/table
- data-testid on ticker page, chart container, analysis
- Frontend still builds clean
</must_haves>
