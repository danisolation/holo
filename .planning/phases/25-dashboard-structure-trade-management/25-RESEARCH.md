# Phase 25: Dashboard Structure & Trade Management - Research

**Researched:** 2025-01-27
**Domain:** Next.js frontend — dashboard UI, data tables, tabs, form management
**Confidence:** HIGH

## Summary

Phase 25 is a frontend-focused phase implementing a paper trading dashboard with tabbed navigation, a sortable/filterable trade list table, settings form, and signal outcome history on the ticker detail page. The backend API (built in Phase 24) provides all necessary endpoints except a symbol filter for trades (needed for UI-05).

The project has well-established patterns for all required functionality: `@tanstack/react-table` for sortable tables (see `trade-history.tsx`), `@base-ui/react` Tabs via shadcn (see `performance-chart.tsx`), `@tanstack/react-query` hooks in `hooks.ts`, and a centralized `apiFetch<T>()` pattern in `api.ts`. This phase follows existing patterns closely with no new dependencies.

**Primary recommendation:** Mirror the existing `trade-history.tsx` + `portfolio/page.tsx` patterns to build the paper trading dashboard. Add a `symbol` query param to the existing `list_trades` backend endpoint for UI-05 rather than creating a new endpoint.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **Routing**: Next.js App Router at `src/app/dashboard/paper-trading/page.tsx`
- **Data fetching**: `@tanstack/react-query` hooks in `src/lib/hooks.ts`
- **API client**: `apiFetch<T>()` in `src/lib/api.ts`
- **UI components**: shadcn/ui (Card, Table, Tabs, Badge, Skeleton, Input, Button)
- **State**: zustand for client-side state, react-query for server state
- **Icons**: lucide-react
- **Charts**: Recharts for non-financial, lightweight-charts for candlestick
- **Styling**: Tailwind CSS v4, Vietnamese labels matching existing pages
- **Navigation**: Add "Paper Trading" link to NAV_LINKS in navbar.tsx at `/dashboard/paper-trading`
- **Tab Structure**: Phase 25 implements Overview + Trades + Settings tabs; Phase 26 implements Analytics + Calendar (but tab headers created now)
- **No new npm dependencies needed**

### Agent's Discretion
- Signal outcome on ticker page approach: add `symbol` filter to existing endpoint vs new endpoint
- Component decomposition within the page (how many component files)
- Table column widths and responsive breakpoints
- Loading/empty state messaging (Vietnamese)

### Deferred Ideas (OUT OF SCOPE)
- Analytics charts (Phase 26)
- Calendar heatmap (Phase 26)
- Fee simulation (ADV-01)
- Multiple virtual accounts (ADV-02)
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| UI-01 | Dashboard page at `/dashboard/paper-trading` with tabs: Overview, Trades, Analytics, Calendar, Settings | Existing Tabs pattern in shadcn/ui (base-ui), page at `src/app/dashboard/paper-trading/page.tsx` |
| UI-05 | Signal outcome history on ticker detail page — 10 recent signals with ✅/❌ | Ticker page at `src/app/ticker/[symbol]/page.tsx`, needs backend `symbol` filter on list_trades |
| UI-07 | Trade list table (sortable, filterable) — symbol, direction, entry, exit, P&L, status, AI score | Exact pattern in `trade-history.tsx` using @tanstack/react-table 8.21.3 |
| UI-08 | Settings form — initial capital, auto-track on/off, min confidence threshold | Backend `GET/PUT /api/paper-trading/config` ready, use react-query mutation pattern |
</phase_requirements>

## Standard Stack

### Core (all already installed — NO new deps)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| next | 16.2.3 | App Router, file-based routing | Project framework [VERIFIED: node_modules] |
| @tanstack/react-query | 5.99.0 | Server state, caching, mutations | Existing hooks.ts pattern [VERIFIED: node_modules] |
| @tanstack/react-table | 8.21.3 | Headless table with sort/filter | Already used in 3 components [VERIFIED: node_modules] |
| zustand | 5.0.12 | Client-side state (table filters persist) | Existing store.ts pattern [VERIFIED: node_modules] |
| tailwindcss | 4.x | Utility-first CSS | Project styling [VERIFIED: package.json] |
| lucide-react | 1.8.0 | Icons | Project icons [VERIFIED: package.json] |
| recharts | 3.8.1 | Charts (for overview sparklines if needed) | Project charts [VERIFIED: package.json] |
| date-fns | 4.1.0 | Date formatting | Already available [VERIFIED: package.json] |

### shadcn/ui Components (already generated in `src/components/ui/`)
| Component | File | Usage in This Phase |
|-----------|------|---------------------|
| Tabs, TabsList, TabsTrigger, TabsContent | `tabs.tsx` | Dashboard tab navigation |
| Table, TableHeader, TableBody, etc. | `table.tsx` | Trade list rendering |
| Card, CardHeader, CardContent, CardTitle | `card.tsx` | Summary cards, settings panel |
| Badge | `badge.tsx` | Status/direction badges |
| Button | `button.tsx` | Sort buttons, actions, filters |
| Input | `input.tsx` | Settings form fields, table filter |
| Skeleton | `skeleton.tsx` | Loading states |
| Dialog | `dialog.tsx` | Trade detail/close confirm |
| Separator | `separator.tsx` | Section dividers |

**Installation:** None needed — all dependencies already in `package.json` and `node_modules/`.

## Architecture Patterns

### Recommended Project Structure
```
frontend/src/
├── app/dashboard/paper-trading/
│   └── page.tsx                    # Main page with Tabs
├── components/
│   ├── paper-trading/
│   │   ├── pt-overview-tab.tsx     # Overview tab: summary cards (win rate, P&L, trades)
│   │   ├── pt-trades-table.tsx     # Trade list table (UI-07)
│   │   ├── pt-settings-form.tsx    # Settings form (UI-08)
│   │   └── pt-signal-outcomes.tsx  # Signal outcome history for ticker page (UI-05)
│   └── ...existing components
├── lib/
│   ├── api.ts                      # Add paper trading types + fetch functions
│   └── hooks.ts                    # Add paper trading hooks
└── ...
```

### Pattern 1: Page with Tabs (UI-01)
**What:** Single "use client" page component using shadcn Tabs
**When to use:** Dashboard pages with multiple content areas
**Example:**
```typescript
// Source: existing performance-chart.tsx pattern + shadcn tabs.tsx
"use client";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";

export default function PaperTradingPage() {
  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold tracking-tight">Paper Trading</h2>
        <p className="text-sm text-muted-foreground mt-1">
          Giả lập và theo dõi hiệu quả tín hiệu AI
        </p>
      </div>
      <Tabs defaultValue="overview">
        <TabsList>
          <TabsTrigger value="overview">Tổng quan</TabsTrigger>
          <TabsTrigger value="trades">Lệnh</TabsTrigger>
          <TabsTrigger value="analytics" disabled>Phân tích</TabsTrigger>
          <TabsTrigger value="calendar" disabled>Lịch</TabsTrigger>
          <TabsTrigger value="settings">Cài đặt</TabsTrigger>
        </TabsList>
        <TabsContent value="overview"><PTOverviewTab /></TabsContent>
        <TabsContent value="trades"><PTTradesTable /></TabsContent>
        <TabsContent value="settings"><PTSettingsForm /></TabsContent>
      </Tabs>
    </div>
  );
}
```

### Pattern 2: Sortable/Filterable Table with @tanstack/react-table (UI-07)
**What:** Headless table with column sort, external filter controls
**When to use:** Data tables with server-side data
**Example (from existing trade-history.tsx):**
```typescript
// Source: frontend/src/components/trade-history.tsx [VERIFIED: codebase]
import {
  useReactTable,
  getCoreRowModel,
  getSortedRowModel,
  flexRender,
  type ColumnDef,
  type SortingState,
} from "@tanstack/react-table";

const [sorting, setSorting] = useState<SortingState>([]);

const columns: ColumnDef<PaperTradeResponse>[] = [
  {
    accessorKey: "symbol",
    header: "Mã CK",
    cell: ({ row }) => <span className="font-mono font-bold">{row.original.symbol}</span>,
  },
  {
    accessorKey: "entry_price",
    header: ({ column }) => (
      <Button variant="ghost" size="sm" onClick={() => column.toggleSorting()} className="-ml-3">
        Entry <ArrowUpDown className="ml-1 size-3" />
      </Button>
    ),
    cell: ({ row }) => <span className="font-mono">{formatVND(row.original.entry_price)}</span>,
  },
  // ... more columns
];

const table = useReactTable({
  data: trades,
  columns,
  state: { sorting },
  onSortingChange: setSorting,
  getCoreRowModel: getCoreRowModel(),
  getSortedRowModel: getSortedRowModel(),
});
```

### Pattern 3: API Types + Hooks (adding paper trading)
**What:** TypeScript interfaces mirroring backend Pydantic schemas, fetch functions, react-query hooks
**When to use:** Every new backend integration
**Example:**
```typescript
// In api.ts — types matching backend PaperTradeResponse schema
export interface PaperTradeResponse {
  id: number;
  symbol: string;
  direction: "long" | "bearish";
  status: string;
  entry_price: number;
  stop_loss: number;
  take_profit_1: number;
  take_profit_2: number;
  adjusted_stop_loss: number | null;
  quantity: number;
  closed_quantity: number;
  realized_pnl: number | null;
  realized_pnl_pct: number | null;
  exit_price: number | null;
  partial_exit_price: number | null;
  signal_date: string;
  entry_date: string | null;
  closed_date: string | null;
  confidence: number;
  timeframe: string;
  position_size_pct: number;
  risk_reward_ratio: number;
  created_at: string;
}

// Fetch function matching existing pattern
export async function fetchPaperTrades(params?: {
  status?: string;
  direction?: string;
  timeframe?: string;
  symbol?: string;
  limit?: number;
  offset?: number;
}): Promise<PaperTradeListResponse> {
  const searchParams = new URLSearchParams();
  if (params?.status) searchParams.set("status", params.status);
  // ... add all params
  const qs = searchParams.toString();
  return apiFetch<PaperTradeListResponse>(`/paper-trading/trades${qs ? `?${qs}` : ""}`);
}

// In hooks.ts — react-query hook
export function usePaperTrades(params?: { ... }) {
  return useQuery({
    queryKey: ["paper-trades", params],
    queryFn: () => fetchPaperTrades(params),
    staleTime: 1 * 60 * 1000,
  });
}
```

### Pattern 4: Mutation with Cache Invalidation
**What:** useMutation with queryClient.invalidateQueries on success
**When to use:** Config updates, trade close actions
**Example (from existing hooks.ts):**
```typescript
export function useUpdatePaperConfig() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: SimulationConfigUpdateRequest) => updatePaperConfig(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["paper-config"] });
      queryClient.invalidateQueries({ queryKey: ["paper-trades"] });
    },
  });
}
```

### Pattern 5: Tabs Props with @base-ui/react
**What:** The shadcn Tabs in this project wraps `@base-ui/react/tabs` — NOT radix-ui
**Critical detail:** Tabs uses `defaultValue` prop (string) and TabsTrigger uses `value` prop
**Verified:** `tabs.tsx` line 3 imports from `@base-ui/react/tabs` [VERIFIED: codebase]

### Anti-Patterns to Avoid
- **Don't use getFilteredRowModel for server-side filtering:** The trade list uses server-side filtering (API query params). Use react-query with filter state in queryKey, not client-side filtering.
- **Don't create separate route files for each tab:** Use a single page with client-side Tabs, not nested routes. This matches the existing portfolio page pattern.
- **Don't import from `@radix-ui`:** This project uses `@base-ui/react` — the shadcn components are generated for base-ui, not radix.
- **Don't hand-roll controlled form state:** Use native React `useState` for simple 3-field forms (no need for react-hook-form or formik for this).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Table sorting | Custom sort comparators | `@tanstack/react-table` `getSortedRowModel()` | Handles multi-column, direction toggle, stable sort |
| Data caching/staleness | Manual cache with useEffect | `@tanstack/react-query` with staleTime | Handles refetching, background updates, dedup |
| Status badge styling | Manual if/else color logic | Lookup object `STATUS_CONFIG[status]` | Maintainable, consistent, type-safe |
| Number formatting (VND) | Template literals | `Intl.NumberFormat("vi-VN")` | Existing `formatVND()` pattern in codebase |
| Tab state routing | URL params + useRouter | shadcn `<Tabs defaultValue="overview">` | Simpler, client-side only, no page reload |

**Key insight:** Every pattern needed for this phase already exists in the codebase. The task is assembly and adaptation, not invention.

## Common Pitfalls

### Pitfall 1: Tabs Component API Mismatch
**What goes wrong:** Using Radix-ui Tabs API (e.g., `<Tabs.Root>`) instead of base-ui wrapper
**Why it happens:** Many online shadcn examples use Radix primitives, but this project uses `@base-ui/react`
**How to avoid:** Use ONLY the exported wrappers: `<Tabs>`, `<TabsList>`, `<TabsTrigger value="...">`, `<TabsContent value="...">`
**Warning signs:** TypeScript errors about missing props, runtime "not a function" errors

### Pitfall 2: Missing Symbol Filter in Backend
**What goes wrong:** UI-05 needs trades filtered by symbol, but current API only filters by status/direction/timeframe
**Why it happens:** The Phase 24 API was designed for the dashboard view, not ticker-specific views
**How to avoid:** Add `symbol` query param to `GET /paper-trading/trades` endpoint AND the service `list_trades` method
**Warning signs:** Fetching all trades and filtering client-side (slow, wasteful)

### Pitfall 3: Query Key Collisions
**What goes wrong:** Different paper-trading hooks share query keys, causing unwanted cache invalidation
**Why it happens:** Using generic key like `["paper-trades"]` without params
**How to avoid:** Include ALL filter params in queryKey: `["paper-trades", { status, direction, symbol, ... }]`
**Warning signs:** Tables refreshing when changing tabs, stale data after filter change

### Pitfall 4: Rendering All Tab Content Eagerly
**What goes wrong:** All tabs fetch data on mount even when not visible, causing unnecessary API calls
**Why it happens:** React renders all TabsContent children by default
**How to avoid:** The `@base-ui/react` Tabs lazily mounts panel content — only the active tab's content renders. But react-query hooks inside might still fire if `enabled` isn't conditional.
**Warning signs:** Network tab showing analytics API calls on first page load

### Pitfall 5: Vietnamese Number Formatting
**What goes wrong:** P&L shows "1234567" instead of "1.234.567" (VN uses dots for thousands)
**Why it happens:** Forgetting to use `Intl.NumberFormat("vi-VN")`
**How to avoid:** Use existing `formatVND()` helper (already in `trade-history.tsx`)
**Warning signs:** Numbers without thousand separators or using commas instead of dots

### Pitfall 6: Badge Status Colors Without Type Safety
**What goes wrong:** Unknown status values render with no styling, or crash
**Why it happens:** Backend returns string statuses like "closed_tp2", "closed_sl", etc.
**How to avoid:** Create a STATUS_CONFIG map covering all 7 possible statuses with fallback
**Warning signs:** Unstyled badges, console warnings about unknown enum values

## Code Examples

### Trade Status Badge Configuration
```typescript
// Source: derived from backend TradeStatus enum [VERIFIED: codebase]
const STATUS_CONFIG: Record<string, { label: string; className: string }> = {
  pending: { label: "Chờ", className: "text-yellow-600 bg-yellow-600/10" },
  active: { label: "Đang mở", className: "text-blue-600 bg-blue-600/10" },
  partial_tp: { label: "Chốt 1 phần", className: "text-cyan-600 bg-cyan-600/10" },
  closed_tp2: { label: "Chốt TP2", className: "text-[#26a69a] bg-[#26a69a]/10" },
  closed_sl: { label: "Cắt lỗ", className: "text-[#ef5350] bg-[#ef5350]/10" },
  closed_timeout: { label: "Hết hạn", className: "text-orange-600 bg-orange-600/10" },
  closed_manual: { label: "Đóng tay", className: "text-gray-600 bg-gray-600/10" },
};
```

### Settings Form with Mutation
```typescript
// Source: existing mutation pattern from hooks.ts [VERIFIED: codebase]
export function PTSettingsForm() {
  const { data: config, isLoading } = usePaperConfig();
  const updateConfig = useUpdatePaperConfig();

  const [capital, setCapital] = useState("");
  const [autoTrack, setAutoTrack] = useState(true);
  const [minConfidence, setMinConfidence] = useState(5);

  // Sync form state when data loads
  useEffect(() => {
    if (config) {
      setCapital(String(config.initial_capital));
      setAutoTrack(config.auto_track_enabled);
      setMinConfidence(config.min_confidence_threshold);
    }
  }, [config]);

  const handleSave = () => {
    updateConfig.mutate({
      initial_capital: Number(capital),
      auto_track_enabled: autoTrack,
      min_confidence_threshold: minConfidence,
    });
  };
  // ...render form
}
```

### Signal Outcome History (UI-05)
```typescript
// Source: ticker detail page pattern [VERIFIED: codebase]
export function PTSignalOutcomes({ symbol }: { symbol: string }) {
  const { data, isLoading } = usePaperTrades({ symbol, limit: 10 });

  if (isLoading) return <Skeleton className="h-32 rounded-xl" />;
  if (!data?.trades.length) return null;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Kết quả tín hiệu gần đây</CardTitle>
      </CardHeader>
      <CardContent className="space-y-2">
        {data.trades.map((trade) => (
          <div key={trade.id} className="flex items-center justify-between text-sm">
            <span>{trade.signal_date}</span>
            <Badge variant="secondary" className={trade.direction === "long" ? "text-[#26a69a]" : "text-[#ef5350]"}>
              {trade.direction.toUpperCase()}
            </Badge>
            <span>
              {trade.realized_pnl != null
                ? trade.realized_pnl > 0 ? "✅" : "❌"
                : "⏳"}
            </span>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}
```

### Navigation Link Addition
```typescript
// Source: frontend/src/components/navbar.tsx line 22-29 [VERIFIED: codebase]
const NAV_LINKS = [
  { href: "/", label: "Tổng quan" },
  { href: "/watchlist", label: "Danh mục" },
  { href: "/dashboard", label: "Bảng điều khiển" },
  { href: "/dashboard/portfolio", label: "Đầu tư" },
  { href: "/dashboard/paper-trading", label: "Paper Trading" },  // NEW
  { href: "/dashboard/corporate-events", label: "Sự kiện" },
  { href: "/dashboard/health", label: "Hệ thống" },
];
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| @radix-ui primitives | @base-ui/react primitives | Project convention | Must use `@base-ui/react` imports, not radix |
| React 18 + use() | React 19 + use() for promises | This project uses React 19 | `params` is Promise in page components |
| tanstack/react-table v7 | v8 (headless, ColumnDef) | v8 stable 2022 | Column definitions are objects, not jsx |
| shadcn v0 (copy-paste) | shadcn v4 (CLI-managed) | This project | Components in `src/components/ui/` with base-ui |

## Backend Modification Required (UI-05)

The existing `GET /api/paper-trading/trades` endpoint needs a `symbol` query parameter for UI-05 (signal outcomes by ticker). This is a minimal change:

**Backend change needed:**
```python
# In paper_trading.py router — add symbol param
@router.get("/trades", response_model=PaperTradeListResponse)
async def list_trades(
    status: str | None = Query(None),
    direction: str | None = Query(None, pattern="^(long|bearish)$"),
    timeframe: str | None = Query(None, pattern="^(swing|position)$"),
    symbol: str | None = Query(None, description="Filter by ticker symbol"),  # NEW
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):

# In paper_trade_analytics_service.py — add symbol filter to query
if symbol:
    query = query.where(Ticker.symbol == symbol.upper())
    count_query = count_query.join(Ticker, PaperTrade.ticker_id == Ticker.id).where(Ticker.symbol == symbol.upper())
```

[VERIFIED: reviewed `list_trades` service method — it already joins Ticker table, so adding `.where(Ticker.symbol == symbol.upper())` is trivial]

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `@base-ui/react` Tabs lazily renders inactive TabsContent panels | Pitfalls | If eager, all tab data fetches on mount — add `enabled` conditionals |
| A2 | Adding symbol filter to backend counts as "in scope" for a frontend-focused phase | Backend Modification | If out of scope, UI-05 would need to fetch all trades client-side |

## Open Questions

1. **Should the disabled tabs (Analytics, Calendar) show placeholder content or nothing?**
   - What we know: Phase 26 will implement these tabs
   - What's unclear: Whether a "Coming soon" placeholder or empty panel is preferred
   - Recommendation: Show a brief "Sắp có" (Coming soon) card in the disabled tab content as a polished touch

2. **Does the navbar highlight work correctly with nested routes?**
   - What we know: Current `pathname === link.href` comparison is exact match
   - What's unclear: Whether `/dashboard/paper-trading` will highlight when on that page (it should, since it's an exact match)
   - Recommendation: Verify that exact match `===` works. If highlighting parent "Bảng điều khiển" is also desired, use `startsWith` — but existing portfolio link doesn't do this, so follow the same pattern.

## Environment Availability

Step 2.6: SKIPPED — This is a frontend code/config phase with no external tool dependencies beyond the already-installed npm packages.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | None configured for frontend (no jest/vitest config found) |
| Config file | None |
| Quick run command | `cd frontend && npx next build` (type-check + build) |
| Full suite command | `cd frontend && npx next build` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| UI-01 | Dashboard page renders with tabs | smoke | `next build` (compile check) | ❌ Wave 0 |
| UI-05 | Signal outcomes render on ticker page | smoke | `next build` (compile check) | ❌ Wave 0 |
| UI-07 | Trade table renders with sort/filter | smoke | `next build` (compile check) | ❌ Wave 0 |
| UI-08 | Settings form saves config | smoke | `next build` (compile check) | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `cd frontend && npx next build` (ensures TypeScript compiles)
- **Per wave merge:** Same — no test suite configured
- **Phase gate:** Successful `next build` + manual visual verification

### Wave 0 Gaps
- No frontend test framework is configured (no jest, vitest, or playwright)
- Validation relies on TypeScript compilation (`next build`) and manual review
- This matches project convention — no existing test files in the frontend

## Sources

### Primary (HIGH confidence)
- `frontend/src/components/trade-history.tsx` — react-table pattern with sorting, filtering, shadcn Table
- `frontend/src/lib/api.ts` — all type definitions and apiFetch pattern
- `frontend/src/lib/hooks.ts` — react-query hook patterns with staleTime, queryKey
- `frontend/src/components/ui/tabs.tsx` — Tabs component API (base-ui)
- `frontend/src/app/dashboard/portfolio/page.tsx` — dashboard sub-page pattern
- `frontend/src/app/ticker/[symbol]/page.tsx` — ticker detail page structure
- `backend/app/schemas/paper_trading.py` — Pydantic schemas to mirror
- `backend/app/api/paper_trading.py` — endpoint signatures and query params
- `backend/app/services/paper_trade_analytics_service.py` — service method for list_trades

### Secondary (MEDIUM confidence)
- shadcn/ui docs for @base-ui/react Tabs usage [ASSUMED: based on generated component code]

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries verified in node_modules with exact versions
- Architecture: HIGH — all patterns taken directly from existing codebase
- Pitfalls: HIGH — identified from actual code review of existing implementations

**Research date:** 2025-01-27
**Valid until:** 2025-02-27 (stable — no dep changes expected)
