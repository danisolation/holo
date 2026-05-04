# Phase 54: Sector Grouping & Heatmap Rework - Research

**Researched:** 2025-07-25
**Domain:** Full-stack feature (FastAPI backend + Next.js frontend) — inline editing, combobox auto-suggest, heatmap data source rework
**Confidence:** HIGH

## Summary

This phase requires backend API changes (PATCH endpoint for sector_group, sectors list endpoint) and frontend UI changes (inline-editable sector column in watchlist table, sector-grouped heatmap filtered to watchlist only). The groundwork is already laid: migration 026 added the `sector_group` column to `user_watchlist`, and the tickers table already stores ICB sector/industry data from vnstock. The existing heatmap component has the grouping logic — it just needs a different data source and grouping key.

The main complexity lies in the **inline editing UX** — combining a combobox (auto-suggest from ICB sectors + custom input) with the @tanstack/react-table cell rendering. The project already uses cmdk + @base-ui/react Popover (shadcn v4), which provides the exact building blocks for a combobox. The heatmap rework is straightforward: change from fetching all market tickers to fetching watchlist tickers joined with market data, then group by `sector_group` instead of `ticker.sector`.

**Primary recommendation:** Use a Popover + Command combobox pattern (same building blocks as ticker-search.tsx) for sector inline editing, add a PATCH endpoint for sector_group updates, and rework the home page to combine watchlist + market-overview data for a filtered heatmap.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- All decisions at agent's discretion (no locked choices from discuss-phase)
- UI should follow existing shadcn/ui + Tailwind patterns in the codebase
- Heatmap uses lightweight-charts or existing charting approach

### Agent's Discretion
- Full discretion on implementation approach

### Deferred Ideas (OUT OF SCOPE)
- None specified
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| TAG-01 | User can assign sector/industry group to each watchlist ticker via inline editing | PATCH `/api/watchlist/{symbol}` endpoint + combobox cell in @tanstack/react-table |
| TAG-02 | When adding a ticker, sector auto-suggests from vnstock ICB classification data | GET `/api/tickers/sectors` endpoint + cmdk Command combobox; ICB data already in tickers.sector |
| TAG-03 | Heatmap displays only watchlist tickers, grouped by sector | Frontend joins watchlist + market-overview data, groups by `sector_group`; existing Heatmap component pattern reused |
</phase_requirements>

## Standard Stack

### Core (Already in project — no new dependencies)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| @tanstack/react-table | ^8.21.3 | Watchlist table with inline editing | Already used in watchlist-table.tsx [VERIFIED: package.json] |
| @tanstack/react-query | ^5.99.0 | Data fetching, mutations, cache invalidation | Already used for all API hooks [VERIFIED: package.json] |
| cmdk | ^1.1.1 | Command palette / combobox primitives | Already used in command.tsx + ticker-search.tsx [VERIFIED: package.json] |
| @base-ui/react | ^1.4.0 | Popover primitives (shadcn v4) | Already used in popover.tsx [VERIFIED: package.json] |
| FastAPI | ~0.135 | Backend API framework | Already in use [VERIFIED: codebase] |
| SQLAlchemy | ~2.0 | ORM for DB operations | Already in use [VERIFIED: codebase] |

### No New Dependencies Required

This phase requires zero new npm or pip packages. All UI primitives (Popover, Command, Table, Input) and backend tools (SQLAlchemy, Pydantic, FastAPI) are already available. [VERIFIED: codebase inspection]

## Architecture Patterns

### Recommended Changes Structure
```
backend/
├── app/
│   ├── models/
│   │   └── user_watchlist.py      # ADD sector_group field to model
│   ├── schemas/
│   │   └── watchlist.py           # ADD sector_group to response/request schemas
│   └── api/
│       ├── watchlist.py           # ADD PATCH endpoint + update add endpoint
│       └── tickers.py             # ADD GET /sectors endpoint
frontend/
├── src/
│   ├── lib/
│   │   ├── api.ts                 # ADD sector types, updateSectorGroup, fetchSectors functions
│   │   └── hooks.ts               # ADD useUpdateSectorGroup, useSectors hooks
│   ├── components/
│   │   ├── sector-combobox.tsx     # NEW: reusable combobox for sector selection
│   │   ├── watchlist-table.tsx     # MODIFY: add sector column with inline editing
│   │   └── heatmap.tsx            # MODIFY: accept sector_group for grouping key
│   └── app/
│       └── page.tsx               # MODIFY: fetch watchlist data, pass to heatmap
```

### Pattern 1: Backend PATCH Endpoint for Sector Group
**What:** Add a PATCH endpoint to update `sector_group` on a watchlist item
**When to use:** User edits sector inline in the watchlist table
**Example:**
```python
# Source: Existing watchlist.py pattern + standard FastAPI PATCH
@router.patch("/{symbol}", response_model=WatchlistItemResponse)
async def update_watchlist_item(symbol: str, body: WatchlistUpdateRequest):
    """Update sector_group for a watchlist item."""
    symbol = symbol.upper().strip()
    async with async_session() as session:
        stmt = select(UserWatchlist).where(UserWatchlist.symbol == symbol)
        result = await session.execute(stmt)
        item = result.scalar_one_or_none()
        if not item:
            raise HTTPException(status_code=404, detail=f"'{symbol}' not in watchlist")
        item.sector_group = body.sector_group
        await session.commit()
        await session.refresh(item)
        # Return enriched response (reuse _get_enriched_watchlist pattern or simple response)
```
[VERIFIED: Follows existing endpoint patterns in backend/app/api/watchlist.py]

### Pattern 2: Sectors List Endpoint from Tickers Table
**What:** GET endpoint returning distinct ICB sector names from the tickers table
**When to use:** Frontend needs auto-suggest options for sector combobox
**Example:**
```python
# Source: Existing tickers.py pattern
@router.get("/sectors", response_model=list[str])
async def list_sectors():
    """Return distinct sector names from active tickers (ICB classification)."""
    async with async_session() as session:
        stmt = (
            select(Ticker.sector)
            .where(Ticker.is_active.is_(True), Ticker.sector.isnot(None))
            .distinct()
            .order_by(Ticker.sector)
        )
        result = await session.execute(stmt)
        return [row[0] for row in result.all()]
```
[VERIFIED: tickers.sector already populated from ICB icb_name2 data via ticker_service.py]

### Pattern 3: Combobox with cmdk + Popover (Inline Table Cell)
**What:** shadcn v4 combobox pattern using existing Command + Popover components
**When to use:** Sector auto-suggest in watchlist table cell
**Example:**
```tsx
// Source: Existing components (command.tsx, popover.tsx, ticker-search.tsx)
// The project already uses cmdk for CommandDialog in ticker-search.
// A cell-level combobox follows the same pattern but with Popover instead of Dialog.
function SectorCombobox({ value, onChange, sectors }: {
  value: string | null;
  onChange: (sector: string | null) => void;
  sectors: string[];
}) {
  const [open, setOpen] = useState(false);
  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger>
        <Button variant="ghost" size="sm" className="justify-start truncate">
          {value || "Chọn ngành..."}
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-[200px] p-0">
        <Command>
          <CommandInput placeholder="Tìm ngành..." />
          <CommandList>
            <CommandEmpty>Không tìm thấy.</CommandEmpty>
            <CommandGroup>
              {sectors.map((sector) => (
                <CommandItem
                  key={sector}
                  value={sector}
                  onSelect={() => { onChange(sector); setOpen(false); }}
                >
                  {sector}
                </CommandItem>
              ))}
            </CommandGroup>
          </CommandList>
        </Command>
      </PopoverContent>
    </Popover>
  );
}
```
[VERIFIED: cmdk ^1.1.1, @base-ui/react ^1.4.0, components exist in project]

### Pattern 4: Heatmap Data Source Rework
**What:** Instead of showing all market tickers, show only watchlist tickers with their sector_group
**When to use:** Home page heatmap
**Key insight:** The `watchlist-table.tsx` already demonstrates the join pattern — it fetches watchlist + market-overview, then filters market data to watchlist symbols only. The heatmap needs the same approach, but groups by `sector_group` (from watchlist) instead of `sector` (from tickers).

```tsx
// Source: Existing pattern from watchlist-table.tsx (lines 46-52)
// Home page combines: useWatchlist() + useMarketOverview()
const heatmapData = useMemo(() => {
  if (!marketData || !watchlistData) return [];
  const marketMap = new Map(marketData.map((t) => [t.symbol, t]));
  return watchlistData
    .map((w) => {
      const market = marketMap.get(w.symbol);
      if (!market) return null;
      return { ...market, sector: w.sector_group ?? market.sector ?? "Khác" };
    })
    .filter(Boolean);
}, [marketData, watchlistData]);
```
[VERIFIED: watchlist-table.tsx lines 46-52 already do this exact join]

### Pattern 5: React Query Optimistic Update + Cache Invalidation
**What:** When user changes sector_group, immediately update UI, then sync to server
**When to use:** Inline sector editing for responsive UX (Success Criteria #4)
```tsx
// Source: Existing mutation pattern from hooks.ts
export function useUpdateSectorGroup() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ symbol, sectorGroup }: { symbol: string; sectorGroup: string | null }) =>
      updateWatchlistSector(symbol, sectorGroup),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["watchlist"] });
    },
  });
}
```
[VERIFIED: Follows exact pattern of useRemoveFromWatchlist in hooks.ts lines 451-458]

### Anti-Patterns to Avoid
- **Don't create a separate heatmap API endpoint:** The frontend already joins watchlist + market-overview efficiently. Adding a backend endpoint duplicates the market-overview query logic and creates a maintenance burden. [VERIFIED: watchlist-table.tsx already does this join]
- **Don't use a Dialog for sector editing:** Inline editing should be a click-to-open combobox in the table cell, not a modal dialog. The Dialog would break the flow of editing multiple tickers quickly.
- **Don't hand-roll a dropdown/autocomplete:** cmdk already provides fuzzy search, keyboard navigation, and accessibility. Use the existing Command component.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Combobox with search | Custom dropdown with filter | cmdk Command + Popover | Already in project, handles fuzzy search, keyboard nav, accessibility [VERIFIED: cmdk ^1.1.1 in package.json] |
| Table inline editing | Custom contentEditable cells | @tanstack/react-table custom cell renderer | Already in project, handles state management per-cell [VERIFIED: @tanstack/react-table ^8.21.3 in package.json] |
| Data joining (watchlist + market) | Custom API endpoint | Frontend useMemo join | Pattern already proven in watchlist-table.tsx [VERIFIED: lines 46-52] |
| Cache invalidation | Manual refetch logic | @tanstack/react-query mutations | Already used throughout the project [VERIFIED: hooks.ts] |

## Common Pitfalls

### Pitfall 1: UserWatchlist Model Missing sector_group
**What goes wrong:** The `sector_group` column exists in the DB (migration 026) but is NOT in the Python SQLAlchemy model. Any attempt to read/write `sector_group` via ORM will fail with an AttributeError.
**Why it happens:** Migration was added as preparation for this phase but the model wasn't updated yet.
**How to avoid:** Add `sector_group` to `UserWatchlist` model BEFORE writing any API code.
**Warning signs:** `AttributeError: 'UserWatchlist' has no attribute 'sector_group'`
[VERIFIED: backend/app/models/user_watchlist.py has only id, symbol, created_at]

### Pitfall 2: Popover Uses @base-ui/react, NOT Radix
**What goes wrong:** shadcn v4 combobox examples online use Radix `@radix-ui/react-popover`. This project uses `@base-ui/react`. The API is different.
**Why it happens:** Project is on shadcn v4 which switched from Radix to base-ui. The existing `popover.tsx` uses `import { Popover as PopoverPrimitive } from "@base-ui/react/popover"`.
**How to avoid:** Copy patterns from the existing `popover.tsx` in this project, not from external shadcn examples.
**Warning signs:** Import errors for `@radix-ui/react-popover`
[VERIFIED: frontend/src/components/ui/popover.tsx line 4]

### Pitfall 3: Heatmap Empty State When Watchlist is Empty
**What goes wrong:** If user has no watchlist items, the home page heatmap shows nothing — but the old "full market" heatmap was useful for discovery.
**Why it happens:** Heatmap now filters to watchlist only.
**How to avoid:** Show a clear empty state with a CTA to add tickers, or a link to the watchlist page. Consider keeping the page title/stats visible.
**Warning signs:** Blank home page for new users.

### Pitfall 4: Stale Home Page After Sector Edit on Watchlist Page
**What goes wrong:** User edits sector_group on `/watchlist` page, navigates to home page, but heatmap still shows old grouping.
**Why it happens:** React Query cache for `["watchlist"]` may be stale if navigating between pages.
**How to avoid:** The `useWatchlist()` hook has `staleTime: 2 * 60 * 1000` (2 min). The mutation invalidation already invalidates `["watchlist"]`. Since both pages use the same query key, React Query handles this automatically. But verify staleTime doesn't cause issues — after mutation invalidation, the cache is cleared and will refetch on next mount.
[VERIFIED: hooks.ts line 435 staleTime: 2 * 60 * 1000]

### Pitfall 5: Enriched Watchlist Query Must Include sector_group
**What goes wrong:** The `_get_enriched_watchlist()` function in the watchlist API uses a complex JOIN query that selects specific columns. If `sector_group` isn't added to the SELECT, it won't appear in the response.
**Why it happens:** The function cherry-picks columns from the query result, not using the ORM model directly.
**How to avoid:** Add `UserWatchlist.sector_group` to the `select()` clause in `_get_enriched_watchlist()`.
[VERIFIED: backend/app/api/watchlist.py lines 42-63, explicit column selection]

### Pitfall 6: Add-to-Watchlist Needs sector_group Auto-Assignment
**What goes wrong:** User adds ticker via POST, but no sector_group is set — it's null. The heatmap groups it under "Khác".
**Why it happens:** The add endpoint doesn't look up the ticker's ICB sector to auto-populate sector_group.
**How to avoid:** When adding a ticker via POST, look up the ticker's sector from the tickers table and use it as the default sector_group. User can override later via inline editing. This satisfies TAG-02 (auto-suggest from ICB data).
[VERIFIED: backend/app/api/watchlist.py POST handler creates entry without sector_group]

## Code Examples

### Example 1: Updated UserWatchlist Model
```python
# backend/app/models/user_watchlist.py
# Source: Existing model + migration 026 column definition
class UserWatchlist(Base):
    __tablename__ = "user_watchlist"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(10), unique=True, nullable=False)
    sector_group: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now()
    )
```
[VERIFIED: Column type matches migration 026: sa.String(100), nullable=True]

### Example 2: Updated Pydantic Schemas
```python
# backend/app/schemas/watchlist.py
class WatchlistItemResponse(BaseModel):
    symbol: str
    created_at: str
    sector_group: str | None = None    # NEW
    ai_signal: str | None = None
    ai_score: int | None = None
    signal_date: str | None = None

class WatchlistUpdateRequest(BaseModel):
    """PATCH /api/watchlist/{symbol} request body."""
    sector_group: str | None = Field(None, max_length=100)

class WatchlistAddRequest(BaseModel):
    symbol: str = Field(min_length=1, max_length=10)
    sector_group: str | None = Field(None, max_length=100)  # Optional on add
```

### Example 3: Frontend WatchlistItem Type Update
```typescript
// frontend/src/lib/api.ts
export interface WatchlistItem {
  symbol: string;
  created_at: string;
  sector_group: string | null;  // NEW
  ai_signal: string | null;
  ai_score: number | null;
  signal_date: string | null;
}
```

### Example 4: Watchlist Table Sector Column
```tsx
// Source: Existing column pattern in watchlist-table.tsx
{
  accessorKey: "sector_group",
  header: "Ngành",
  cell: ({ row }) => {
    const watchItem = watchlistData?.find((w) => w.symbol === row.original.symbol);
    return (
      <SectorCombobox
        value={watchItem?.sector_group ?? null}
        onChange={(sector) => updateSectorMutation.mutate({
          symbol: row.original.symbol,
          sectorGroup: sector,
        })}
        sectors={sectorsData ?? []}
      />
    );
  },
  enableSorting: false,
}
```

### Example 5: Home Page Heatmap Rework
```tsx
// frontend/src/app/page.tsx — key change
// Before: <Heatmap data={marketData} />
// After:  <Heatmap data={watchlistHeatmapData} />

const { data: watchlistData } = useWatchlist();
const { data: marketData } = useMarketOverview();

const watchlistHeatmapData = useMemo(() => {
  if (!marketData || !watchlistData) return [];
  const marketMap = new Map(marketData.map((t) => [t.symbol, t]));
  return watchlistData
    .map((w) => {
      const market = marketMap.get(w.symbol);
      if (!market) return null;
      // Override sector with user's sector_group, fallback to ICB sector
      return { ...market, sector: w.sector_group ?? market.sector ?? "Khác" };
    })
    .filter((item): item is MarketTicker => item !== null);
}, [marketData, watchlistData]);
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Heatmap shows all 400 tickers | Heatmap shows only watchlist tickers | Phase 54 | More relevant, personalized view |
| Tickers grouped by ICB sector (from DB) | Tickers grouped by user-assigned sector_group | Phase 54 | User can customize grouping |
| Watchlist has no sector field | Watchlist has editable sector_group | Phase 54 (prep: Phase 52 migration 026) | Enables sector organization |

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | ICB sector data is already populated in tickers.sector for most/all active tickers | Architecture Patterns / Pattern 2 | If sectors are NULL, auto-suggest list will be empty — would need to trigger ticker sync first |
| A2 | cmdk Command component supports being rendered inside a Popover (not just Dialog) | Architecture Patterns / Pattern 3 | Would need to find alternative combobox approach — but this is standard cmdk usage [LOW RISK] |
| A3 | @base-ui/react Popover supports being triggered from within a table cell without z-index or portal issues | Common Pitfalls / Pitfall 2 | May need z-index adjustments; existing PopoverContent uses Portal so should be fine |

## Open Questions

1. **Should the home page show a "full market" heatmap toggle when watchlist is empty?**
   - What we know: Current heatmap shows all ~400 tickers. Rework filters to watchlist only.
   - What's unclear: UX for users with empty watchlist — empty page vs. fallback to full market.
   - Recommendation: Show empty state with CTA. The "full market" view is still accessible via the market overview section (stats cards remain visible). If user has 0 watchlist items, show invitation to add tickers.

2. **Should the add-to-watchlist POST auto-populate sector_group from ICB data?**
   - What we know: Tickers table has sector from ICB. WatchlistAddRequest can accept optional sector_group.
   - What's unclear: Whether to auto-populate server-side or let frontend handle it.
   - Recommendation: Auto-populate server-side in the POST handler by looking up `tickers.sector` for the symbol. This ensures sector_group is always populated without extra frontend work. User can override via inline editing.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (backend), manual testing (frontend) |
| Config file | backend/pytest.ini or pyproject.toml |
| Quick run command | `cd backend && python -m pytest tests/ -x -q` |
| Full suite command | `cd backend && python -m pytest tests/ -v` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| TAG-01 | PATCH /watchlist/{symbol} updates sector_group | unit | `pytest tests/test_watchlist_api.py -x -k "patch"` | ❌ Wave 0 |
| TAG-01 | GET /watchlist returns sector_group in response | unit | `pytest tests/test_watchlist_api.py -x -k "get_enriched"` | ❌ Wave 0 |
| TAG-02 | GET /tickers/sectors returns distinct ICB sectors | unit | `pytest tests/test_tickers_api.py -x -k "sectors"` | ❌ Wave 0 |
| TAG-02 | POST /watchlist auto-populates sector_group from ICB | unit | `pytest tests/test_watchlist_api.py -x -k "add_auto_sector"` | ❌ Wave 0 |
| TAG-03 | Heatmap renders only watchlist tickers grouped by sector | manual | Manual browser test | N/A |

### Sampling Rate
- **Per task commit:** Backend unit tests for modified endpoints
- **Per wave merge:** Full backend test suite
- **Phase gate:** All API tests pass + manual heatmap verification

### Wave 0 Gaps
- [ ] Backend test files for new PATCH endpoint and sectors endpoint
- [ ] Frontend manual test checklist for inline editing + heatmap

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | No | Single-user app, no auth |
| V3 Session Management | No | No sessions |
| V4 Access Control | No | Single-user, no RBAC |
| V5 Input Validation | Yes | Pydantic Field(max_length=100) for sector_group, symbol validation |
| V6 Cryptography | No | No crypto needed |

### Known Threat Patterns

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| SQL Injection via sector_group | Tampering | SQLAlchemy ORM parameterization (already standard in codebase) |
| XSS via sector_group display | Tampering | React auto-escapes JSX content (no dangerouslySetInnerHTML) |
| Oversized input | DoS | Pydantic Field(max_length=100) matches DB column String(100) |

## Sources

### Primary (HIGH confidence)
- backend/app/models/user_watchlist.py — current model (id, symbol, created_at only)
- backend/alembic/versions/026_discovery_results.py — migration adding sector_group column (String(100), nullable)
- backend/app/api/watchlist.py — current CRUD endpoints and _get_enriched_watchlist query
- backend/app/services/ticker_service.py — ICB data mapping (icb_name2 → sector, icb_name3 → industry)
- backend/app/crawlers/vnstock_crawler.py — fetch_industry_classification() returns ICB data
- backend/app/api/tickers.py — MarketTickerResponse schema, market-overview endpoint
- frontend/src/components/heatmap.tsx — current grouping logic (groups by ticker.sector)
- frontend/src/components/watchlist-table.tsx — current table with @tanstack/react-table
- frontend/src/lib/api.ts — WatchlistItem, MarketTicker types and fetch functions
- frontend/src/lib/hooks.ts — useWatchlist, useMarketOverview hooks
- frontend/src/components/ticker-search.tsx — cmdk CommandDialog pattern
- frontend/src/components/ui/popover.tsx — @base-ui/react Popover (NOT Radix)
- frontend/src/components/ui/command.tsx — cmdk Command wrapper
- frontend/package.json — cmdk ^1.1.1, @base-ui/react ^1.4.0, @tanstack/react-table ^8.21.3

### Secondary (MEDIUM confidence)
- shadcn/ui v4 documentation for combobox pattern (Popover + Command) [ASSUMED: standard pattern]

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all dependencies already in project, zero new packages needed
- Architecture: HIGH — patterns verified against existing codebase (watchlist-table join, command dialog, popover)
- Pitfalls: HIGH — identified from direct code inspection (model gap, base-ui vs radix, enriched query columns)

**Research date:** 2025-07-25
**Valid until:** 2025-08-25 (stable — no external dependency changes expected)
