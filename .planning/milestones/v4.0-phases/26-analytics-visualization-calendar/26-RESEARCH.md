# Phase 26: Analytics Visualization & Calendar - Research

**Researched:** 2025-01-27
**Domain:** React data visualization (calendar heatmap, charts, analytics tables)
**Confidence:** HIGH

## Summary

Phase 26 fills the two disabled tabs ("Phân tích" and "Lịch") in the paper-trading page created by Phase 25, and adds 4 new backend analytics endpoints for streak tracking, timeframe comparison, periodic summaries, and calendar data. The frontend visualization layer uses the existing Recharts library (already `^3.8.1` in package.json) for charts plus a new `react-activity-calendar@3.2.0` package for the GitHub-style calendar heatmap. The backend extends the existing `PaperTradeAnalyticsService` with 4 new methods following the exact pattern of the AN-01 through AN-09 implementations from Phase 24.

The existing codebase provides clear patterns to follow: `PerformanceChart` for Recharts `AreaChart` usage, `AllocationChart` for Recharts `PieChart`, `PTOverviewTab` for data fetching with react-query hooks, and the API router structure in `paper_trading.py`. All new code follows these existing patterns directly.

**Primary recommendation:** Add `react-activity-calendar@3.2.0` as the only new dependency, implement 4 new backend service methods + endpoints + schemas, then build `PTAnalyticsTab` and `PTCalendarTab` components to replace the disabled tab placeholders.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **New npm dependency**: `react-activity-calendar@^3.2.0` — GitHub-style contribution calendar heatmap component
- **Backend API already built in Phase 24**: Summary, equity-curve, drawdown, direction, confidence, risk-reward, profit-factor, sector endpoints exist
- **New backend endpoints needed**: Streaks, timeframe, periodic (weekly|monthly), calendar — all 4 must be added
- **Frontend patterns**: React-query hooks, shadcn/ui, Recharts, Vietnamese labels
- **Tab Integration**: Enable disabled "Phân tích" and "Lịch" tabs with real content
- **Only new dep**: react-activity-calendar

### Copilot's Discretion
- Component internal structure and sub-component decomposition
- Exact chart configurations and styling
- Backend query optimization approach

### Deferred Ideas (OUT OF SCOPE)
- Fee simulation (ADV-01)
- Multiple virtual accounts (ADV-02)
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| UI-02 | Calendar heatmap (GitHub-style) — green win days, red loss days, intensity proportional to magnitude | react-activity-calendar@3.2.0 with custom ThemeInput + calendar backend endpoint for daily P&L aggregates |
| UI-03 | Streak tracking — current/longest win/loss streaks, warning when loss streak >5 | New backend `/analytics/streaks` endpoint with SQL window functions on paper_trades ordered by closed_date |
| UI-04 | Timeframe comparison (swing vs position) — side-by-side win rate, avg P&L | New backend `/analytics/timeframe` endpoint grouping by timeframe column |
| UI-06 | Weekly/monthly performance summary tables — win rate, P&L, trade count, avg R:R per period | New backend `/analytics/periodic?period=weekly|monthly` endpoint using date_trunc grouping |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| react-activity-calendar | 3.2.0 | Calendar heatmap (UI-02) | Only dep needed; supports React 19, dark/light themes, custom colors, tooltips [VERIFIED: npm registry] |
| recharts | 3.8.1 | Area/Bar charts (equity curve, drawdowns, breakdowns) | Already installed; used by performance-chart.tsx and allocation-chart.tsx [VERIFIED: package.json] |
| @tanstack/react-query | 5.99.0 | Data fetching hooks | Already installed; all hooks.ts patterns use this [VERIFIED: package.json] |
| date-fns | 4.1.0 | Date formatting/grouping for periodic summaries | Already installed [VERIFIED: package.json] |

### Supporting (already installed)
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| lucide-react | 1.8.0 | Icons (Flame for streak, Calendar, etc.) | Already used throughout |
| shadcn/ui (Card, Table, Badge, Tabs) | N/A | Layout containers, data tables | Already used in PT components |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| react-activity-calendar | Custom SVG grid | Way more code, no tooltip/theme support OOTB |
| Recharts BarChart | visx/d3 | Recharts already in bundle, simpler API for this use case |

**Installation:**
```bash
cd frontend && npm install react-activity-calendar@^3.2.0
```

**Version verification:**
- react-activity-calendar: 3.2.0 (latest, published 2024) [VERIFIED: npm registry]
- recharts: 3.8.1 (already installed) [VERIFIED: npm registry]
- date-fns: 4.1.0 (already installed) [VERIFIED: npm registry]

## Architecture Patterns

### Recommended Project Structure
```
frontend/src/components/paper-trading/
├── pt-overview-tab.tsx          # (existing)
├── pt-trades-table.tsx          # (existing)
├── pt-settings-form.tsx         # (existing)
├── pt-signal-outcomes.tsx       # (existing)
├── pt-analytics-tab.tsx         # NEW: Analytics tab container
├── pt-calendar-tab.tsx          # NEW: Calendar tab container
├── pt-equity-chart.tsx          # NEW: Equity curve + drawdown overlay
├── pt-streak-cards.tsx          # NEW: Streak display cards (UI-03)
├── pt-timeframe-compare.tsx     # NEW: Swing vs Position comparison (UI-04)
├── pt-periodic-table.tsx        # NEW: Weekly/monthly summary table (UI-06)
└── pt-calendar-heatmap.tsx      # NEW: Calendar heatmap wrapper (UI-02)

frontend/src/lib/
├── api.ts                       # Add 4 new fetch functions + types
└── hooks.ts                     # Add 4 new react-query hooks

backend/app/
├── api/paper_trading.py         # Add 4 new endpoint handlers
├── schemas/paper_trading.py     # Add 4 new response schemas
└── services/paper_trade_analytics_service.py  # Add 4 new service methods
```

### Pattern 1: Backend Analytics Query (existing pattern from Phase 24)
**What:** All analytics queries filter by `CLOSED_STATUSES`, group by a dimension, and return dicts
**When to use:** Every new endpoint follows this
**Example:**
```python
# Source: backend/app/services/paper_trade_analytics_service.py (existing pattern)
async def get_streaks(self) -> dict:
    """Compute win/loss streaks from closed trades ordered by closed_date."""
    result = await self.session.execute(
        select(PaperTrade.closed_date, PaperTrade.realized_pnl)
        .where(
            PaperTrade.status.in_(CLOSED_STATUSES),
            PaperTrade.closed_date.isnot(None),
        )
        .order_by(PaperTrade.closed_date)
    )
    rows = result.all()
    # Iterate to compute current and max streaks...
```

### Pattern 2: Frontend React-Query Hook (existing pattern)
**What:** Each analytics endpoint gets a dedicated hook with 1-5 min staleTime
**When to use:** Every new data source
**Example:**
```typescript
// Source: frontend/src/lib/hooks.ts (existing pattern)
export function usePaperStreaks() {
  return useQuery({
    queryKey: ["paper-analytics-streaks"],
    queryFn: fetchPaperStreaks,
    staleTime: 1 * 60 * 1000,
  });
}
```

### Pattern 3: Recharts Chart Component (existing pattern from performance-chart.tsx)
**What:** Card wrapper → loading skeleton → ResponsiveContainer → Chart with custom tooltip
**When to use:** Equity curve, drawdown chart, bar charts
**Example:**
```tsx
// Source: frontend/src/components/performance-chart.tsx (lines 73-145)
<Card>
  <CardHeader>...</CardHeader>
  <CardContent>
    {isLoading ? <Skeleton /> : (
      <ResponsiveContainer width="100%" height={320}>
        <AreaChart data={data}>
          <CartesianGrid stroke="var(--border)" strokeDasharray="3 3" />
          <XAxis dataKey="date" tick={{ fontSize: 12 }} />
          <YAxis tickFormatter={formatCompactVND} />
          <Tooltip content={<CustomTooltip />} />
          <Area type="monotone" dataKey="value" stroke="#3b82f6" fill="url(#gradient)" />
        </AreaChart>
      </ResponsiveContainer>
    )}
  </CardContent>
</Card>
```

### Pattern 4: react-activity-calendar Integration
**What:** Map daily P&L to Activity[] format with custom win/loss color theme
**When to use:** Calendar heatmap (UI-02)
**Example:**
```tsx
// Source: react-activity-calendar v3.2.0 API [VERIFIED: npm package types]
import { ActivityCalendar, type Activity, type ThemeInput } from 'react-activity-calendar';

// Data format: { date: "YYYY-MM-DD", count: number, level: 0-4 }
// Level mapping: 0=no trade, 1=small loss, 2=big loss, 3=small win, 4=big win
// For win/loss split: use renderBlock to override colors per-item

const theme: ThemeInput = {
  light: ['#ebedf0', '#9be9a8', '#40c463', '#30a14e', '#216e39'], // green (wins)
  dark: ['#161b22', '#0e4429', '#006d32', '#26a641', '#39d353'],
};

// For loss days, use renderBlock to apply red colors
<ActivityCalendar
  data={calendarData}
  theme={theme}
  blockSize={12}
  blockMargin={3}
  showWeekdayLabels={['mon', 'wed', 'fri']}
  labels={{
    months: ['T1','T2','T3','T4','T5','T6','T7','T8','T9','T10','T11','T12'],
    weekdays: ['CN','T2','T3','T4','T5','T6','T7'],
    totalCount: '{{count}} lệnh trong {{year}}',
    legend: { less: 'Ít', more: 'Nhiều' },
  }}
  tooltips={{
    activity: {
      text: (activity) => `${activity.date}: ${activity.count > 0 ? '+' : ''}${activity.count} VND`,
    },
  }}
/>
```

### Pattern 5: Dual-Color Calendar (Wins Green / Losses Red)
**What:** react-activity-calendar only supports one color gradient natively. For win/loss split, use `renderBlock` to override rect fill.
**When to use:** UI-02 requires green for wins, red for losses
**Example:**
```tsx
// Custom renderBlock for win/loss coloring
const WIN_COLORS = ['#ebedf0', '#9be9a8', '#40c463', '#30a14e', '#216e39'];
const LOSS_COLORS = ['#ebedf0', '#fca5a5', '#f87171', '#ef4444', '#dc2626'];

// Backend returns: { date, daily_pnl, level, is_win }
// Map to Activity: level 0=no trade, 1-4=intensity
// Use renderBlock to pick color based on custom data attribute

function renderBlock(block: BlockElement, activity: Activity) {
  // activity.count stores the raw P&L (positive=win, negative=loss)
  const isWin = activity.count >= 0;
  const colors = isWin ? WIN_COLORS : LOSS_COLORS;
  return React.cloneElement(block, {
    style: { ...block.props.style, fill: colors[activity.level] },
  });
}
```

### Anti-Patterns to Avoid
- **Don't fetch all trades client-side to compute streaks**: Let the backend compute — trades could be 100+ rows. Follow existing pattern where analytics are computed server-side.
- **Don't build separate chart pages**: Keep all analytics in the two tabs (Phân tích / Lịch) within the paper-trading page
- **Don't use BarChart for equity curve**: Use AreaChart (consistent with performance-chart.tsx pattern)
- **Don't forget Vietnamese labels**: All text must be in Vietnamese — match the `pt-overview-tab.tsx` pattern

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Calendar heatmap | Custom SVG grid with 365 cells | `react-activity-calendar` | Handles layout, responsive sizing, tooltips, dark mode, localization |
| Date period grouping | Manual week/month iteration | `date-fns` `startOfWeek`/`startOfMonth` + SQL `date_trunc` | Edge cases with year boundaries, locale-aware week starts |
| Streak calculation | Client-side iteration over all trades | Backend SQL/Python with ordered cursor | Server has complete data; client only gets aggregated result |
| Chart tooltips | Custom positioned divs | Recharts `<Tooltip content={<Custom />} />` | Positioning, transitions, responsiveness handled |

**Key insight:** All heavy computation (streaks, periodic aggregates, calendar data) MUST be backend-computed. Frontend only renders pre-computed results.

## Common Pitfalls

### Pitfall 1: react-activity-calendar Single Theme Limitation
**What goes wrong:** The library's `theme` prop only supports one color gradient. If you try to show both green (wins) and red (losses) using only `theme`, all days get the same gradient color.
**Why it happens:** The library was designed for GitHub-style "more is better" single-metric data, not positive/negative values.
**How to avoid:** Use `renderBlock` prop to override the fill color of each rect based on whether daily P&L is positive or negative. Store the win/loss flag in the `count` field (positive = win, negative = loss).
**Warning signs:** All calendar cells show the same color hue.

### Pitfall 2: Calendar Data Gaps
**What goes wrong:** react-activity-calendar expects continuous date ranges — if your data has gaps (no trades on weekends/holidays), the calendar still renders those days but with level 0.
**Why it happens:** The library fills the full year/date range regardless of input data gaps.
**How to avoid:** Backend should return data ONLY for days with closed trades. Frontend maps this sparse data to Activity[] — missing days automatically become level 0 (the desired behavior for "no trades" days).
**Warning signs:** All days showing as active, or error about non-contiguous data.

### Pitfall 3: Empty Data Renders
**What goes wrong:** Charts and calendar crash or show ugly empty states when user has zero closed trades.
**Why it happens:** Division by zero in win rate, empty arrays passed to Recharts/calendar.
**How to avoid:** Always check `data.length === 0` and show the Vietnamese "Chưa có dữ liệu" message (matches existing `performance-chart.tsx` pattern line 103-106). Backend should return sensible empty defaults (0 for counts, empty arrays for lists).
**Warning signs:** NaN in displayed values, blank chart areas.

### Pitfall 4: Streak Computation Edge Cases
**What goes wrong:** Streak count is wrong when multiple trades close on the same day.
**Why it happens:** If you count per-trade rather than per-day, a single day with 3 wins counts as streak of 3. But the requirement says "consecutive days" for UI-02.
**How to avoid:** Compute streak based on per-trade basis (each closed trade is a win/loss event). The "calendar day" concept applies to the heatmap (UI-02) but streaks (UI-03) count individual trade outcomes.
**Warning signs:** User closes 5 trades in one day and sees "5-trade win streak" immediately.

### Pitfall 5: Tab Activation Breaking Existing Functionality
**What goes wrong:** Removing `disabled` from tabs changes default focus behavior or breaks existing tab content.
**Why it happens:** The Tabs component from shadcn/ui may have conditional rendering tied to disabled state.
**How to avoid:** Simply remove `disabled` prop from the two TabsTrigger elements and replace placeholder content in TabsContent. Existing tabs remain unchanged.
**Warning signs:** Other tabs (overview, trades, settings) stop rendering or lose state.

## Code Examples

### Backend: Streak Calculation Service Method
```python
# Pattern follows get_direction_analysis() from existing service
async def get_streaks(self) -> dict:
    """Compute current and longest win/loss streaks."""
    result = await self.session.execute(
        select(PaperTrade.closed_date, PaperTrade.realized_pnl)
        .where(
            PaperTrade.status.in_(CLOSED_STATUSES),
            PaperTrade.closed_date.isnot(None),
            PaperTrade.realized_pnl.isnot(None),
        )
        .order_by(PaperTrade.closed_date, PaperTrade.id)
    )
    rows = result.all()

    current_win = 0
    current_loss = 0
    max_win = 0
    max_loss = 0

    for row in rows:
        if float(row.realized_pnl) > 0:
            current_win += 1
            current_loss = 0
            max_win = max(max_win, current_win)
        else:
            current_loss += 1
            current_win = 0
            max_loss = max(max_loss, current_loss)

    return {
        "current_win_streak": current_win,
        "current_loss_streak": current_loss,
        "longest_win_streak": max_win,
        "longest_loss_streak": max_loss,
        "total_trades": len(rows),
    }
```

### Backend: Timeframe Comparison
```python
# Pattern follows get_direction_analysis() but groups by timeframe
async def get_timeframe_comparison(self) -> list[dict]:
    """Swing vs Position performance comparison."""
    result = await self.session.execute(
        select(
            PaperTrade.timeframe,
            func.count().label("total"),
            func.count().filter(PaperTrade.realized_pnl > 0).label("wins"),
            func.sum(PaperTrade.realized_pnl).label("total_pnl"),
            func.avg(PaperTrade.realized_pnl).label("avg_pnl"),
        )
        .where(PaperTrade.status.in_(CLOSED_STATUSES))
        .group_by(PaperTrade.timeframe)
    )
    return [
        {
            "timeframe": row.timeframe,
            "total_trades": row.total,
            "wins": row.wins or 0,
            "losses": row.total - (row.wins or 0),
            "win_rate": round((row.wins or 0) / row.total * 100, 2) if row.total > 0 else 0,
            "total_pnl": round(float(row.total_pnl or 0), 2),
            "avg_pnl": round(float(row.avg_pnl or 0), 2),
        }
        for row in result.all()
    ]
```

### Backend: Periodic Summary (Weekly/Monthly)
```python
from sqlalchemy import extract, func

async def get_periodic_summary(self, period: str = "weekly") -> list[dict]:
    """Weekly or monthly performance summary."""
    if period == "weekly":
        # ISO week grouping
        period_expr = func.concat(
            extract("isoyear", PaperTrade.closed_date), '-W',
            func.lpad(extract("week", PaperTrade.closed_date).cast(String), 2, '0')
        )
    else:
        period_expr = func.to_char(PaperTrade.closed_date, 'YYYY-MM')

    result = await self.session.execute(
        select(
            period_expr.label("period"),
            func.count().label("total"),
            func.count().filter(PaperTrade.realized_pnl > 0).label("wins"),
            func.sum(PaperTrade.realized_pnl).label("total_pnl"),
            func.avg(PaperTrade.risk_reward_ratio).label("avg_rr"),
        )
        .where(
            PaperTrade.status.in_(CLOSED_STATUSES),
            PaperTrade.closed_date.isnot(None),
        )
        .group_by(period_expr)
        .order_by(period_expr.desc())
        .limit(12)  # Last 12 periods
    )
    return [
        {
            "period": row.period,
            "total_trades": row.total,
            "wins": row.wins or 0,
            "losses": row.total - (row.wins or 0),
            "win_rate": round((row.wins or 0) / row.total * 100, 2) if row.total > 0 else 0,
            "total_pnl": round(float(row.total_pnl or 0), 2),
            "avg_rr": round(float(row.avg_rr or 0), 2),
        }
        for row in result.all()
    ]
```

### Backend: Calendar Data
```python
async def get_calendar_data(self) -> list[dict]:
    """Daily P&L aggregates for calendar heatmap."""
    result = await self.session.execute(
        select(
            PaperTrade.closed_date,
            func.sum(PaperTrade.realized_pnl).label("daily_pnl"),
            func.count().label("trade_count"),
        )
        .where(
            PaperTrade.status.in_(CLOSED_STATUSES),
            PaperTrade.closed_date.isnot(None),
        )
        .group_by(PaperTrade.closed_date)
        .order_by(PaperTrade.closed_date)
    )
    return [
        {
            "date": row.closed_date.isoformat(),
            "daily_pnl": round(float(row.daily_pnl or 0), 2),
            "trade_count": row.trade_count,
        }
        for row in result.all()
    ]
```

### Frontend: Calendar Heatmap Component
```tsx
"use client";

import { ActivityCalendar, type Activity } from 'react-activity-calendar';
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { usePaperCalendar } from "@/lib/hooks";

// Color scales
const WIN_COLORS = ['#ebedf0', '#bbf7d0', '#4ade80', '#16a34a', '#166534'];
const LOSS_COLORS = ['#ebedf0', '#fecaca', '#f87171', '#dc2626', '#991b1b'];

function mapToActivities(data: CalendarDataPoint[]): Activity[] {
  // Find max magnitude for level scaling
  const maxMag = Math.max(...data.map(d => Math.abs(d.daily_pnl)), 1);
  
  return data.map(d => ({
    date: d.date,
    count: d.daily_pnl, // positive=win, negative=loss (used in renderBlock)
    level: Math.min(4, Math.max(1, Math.ceil(Math.abs(d.daily_pnl) / maxMag * 4))),
  }));
}

function renderBlock(block, activity: Activity) {
  if (activity.level === 0) return block;
  const colors = activity.count >= 0 ? WIN_COLORS : LOSS_COLORS;
  return React.cloneElement(block, {
    style: { ...block.props.style, fill: colors[activity.level] },
  });
}
```

### Frontend: Page Tab Activation
```tsx
// In page.tsx — just remove disabled and replace content
<TabsTrigger value="analytics">Phân tích</TabsTrigger>  {/* removed disabled */}
<TabsTrigger value="calendar">Lịch</TabsTrigger>        {/* removed disabled */}

<TabsContent value="analytics">
  <PTAnalyticsTab />
</TabsContent>

<TabsContent value="calendar">
  <PTCalendarTab />
</TabsContent>
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| react-activity-calendar v2 (SVG only) | v3 with @floating-ui tooltips + React 19 support | v3.0 (2024) | Breaking: import changed, tooltip API redesigned |
| Recharts v2 (class components) | Recharts v3 (functional, tree-shakeable) | v3.0 (2024) | Already using v3.8.1 — no migration needed |

**Deprecated/outdated:**
- react-activity-calendar v2: No React 19 support, deprecated tooltip API via `react-tooltip`

## Assumptions Log

> List all claims tagged `[ASSUMED]` in this research.

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | PostgreSQL `extract('week', ...)` and `to_char` functions work with SQLAlchemy async session | Code Examples (periodic) | May need `func.date_trunc` or raw SQL — easily fixable at implementation |
| A2 | react-activity-calendar renderBlock receives `count` field with the original value (can be negative) | Pattern 5 | If library clamps count to 0+, need alternative approach (store sign in level encoding) |
| A3 | The `tooltips.css` import from react-activity-calendar is needed for tooltip styling | Architecture | May need explicit `import 'react-activity-calendar/tooltips.css'` in component |

## Open Questions

1. **Calendar date range boundaries**
   - What we know: react-activity-calendar renders from first to last date in the data array. You can set boundaries by passing Activity with level 0 at start/end.
   - What's unclear: Should we show last 365 days, or current year, or all-time?
   - Recommendation: Show last 365 days (rolling window). Pass `{date: oneYearAgo, count: 0, level: 0}` as first element to anchor the start.

2. **Streak definition granularity**
   - What we know: Trades can be closed multiple per day. CONTEXT.md says "streak tracking" without specifying per-trade or per-day.
   - What's unclear: Does a "5 loss streak" mean 5 consecutive losing trades, or 5 consecutive days with net losses?
   - Recommendation: Count per-trade (each closed trade is one streak unit). This is more granular and standard in trading analytics.

3. **R:R in periodic summary**
   - What we know: UI-06 asks for "avg R:R per period". The `risk_reward_ratio` field on PaperTrade is the *predicted* R:R from the signal.
   - What's unclear: Should this be predicted R:R or achieved R:R?
   - Recommendation: Use predicted R:R (`risk_reward_ratio` column) — it's simpler and gives a sense of the signals being followed. Achieved R:R requires the complex calculation from AN-07.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (backend) |
| Config file | backend/pytest.ini or pyproject.toml |
| Quick run command | `cd backend && python -m pytest tests/ -x --tb=short` |
| Full suite command | `cd backend && python -m pytest tests/ -v` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| UI-02 | Calendar heatmap data endpoint returns daily P&L | unit | `pytest tests/test_paper_analytics.py::test_calendar_data -x` | ❌ Wave 0 |
| UI-03 | Streak endpoint computes correct win/loss streaks | unit | `pytest tests/test_paper_analytics.py::test_streaks -x` | ❌ Wave 0 |
| UI-04 | Timeframe endpoint returns swing vs position breakdown | unit | `pytest tests/test_paper_analytics.py::test_timeframe -x` | ❌ Wave 0 |
| UI-06 | Periodic endpoint returns weekly/monthly grouped data | unit | `pytest tests/test_paper_analytics.py::test_periodic -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `cd backend && python -m pytest tests/test_paper_analytics.py -x --tb=short`
- **Per wave merge:** `cd backend && python -m pytest tests/ -v`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `tests/test_paper_analytics.py` — test new 4 analytics methods (streaks, timeframe, periodic, calendar)
- [ ] Frontend: Manual visual verification (component renders, tabs activate, calendar displays)

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | N/A — single-user local app |
| V3 Session Management | no | N/A |
| V4 Access Control | no | N/A — no auth |
| V5 Input Validation | yes | Pydantic schemas validate `period` query param (weekly|monthly pattern) |
| V6 Cryptography | no | N/A |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| SQL injection via period param | Tampering | Pydantic `Query(pattern="^(weekly|monthly)$")` validation |
| Large dataset DoS (calendar spanning years) | DoS | Backend limits to last 365 days + LIMIT clauses on periodic |

## Sources

### Primary (HIGH confidence)
- npm registry: react-activity-calendar@3.2.0 — version, peerDeps, TypeScript API types [VERIFIED]
- npm registry: recharts@3.8.1 [VERIFIED]
- Existing codebase: `paper_trade_analytics_service.py` — exact patterns for analytics queries
- Existing codebase: `performance-chart.tsx`, `allocation-chart.tsx` — Recharts patterns
- Existing codebase: `hooks.ts`, `api.ts` — react-query hook patterns
- Existing codebase: `paper_trading.py` (router) — endpoint structure

### Secondary (MEDIUM confidence)
- react-activity-calendar GitHub README — usage examples, data format

### Tertiary (LOW confidence)
- None

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all packages verified on npm, most already installed
- Architecture: HIGH — follows exact patterns from Phase 24/25 code already in codebase
- Pitfalls: HIGH — identified from library API analysis and existing code patterns

**Research date:** 2025-01-27
**Valid until:** 2025-02-27 (stable libraries, well-established patterns)
