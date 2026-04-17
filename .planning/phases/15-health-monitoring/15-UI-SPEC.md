# Phase 15 — UI Design Contract: Health & Monitoring

## Scope

Three new UI elements added to the existing health dashboard page:

1. **GeminiUsageCard** — Token & request usage vs free-tier limits
2. **PipelineTimeline** — Gantt-style bar chart of pipeline step durations
3. **HealthAlertBanner** — (Backend-only Telegram alerts; no new frontend component needed)

## Design System Reference

All components follow the project's base-nova shadcn/ui preset, Tailwind CSS 4, dark/light theme support.

### Typography Contract
- 4 sizes: 12px / 14px / 18px / 24px
- 2 weights: 400 (regular) / 600 (semibold)
- **NEVER** use `font-bold` (700) — always `font-semibold`

### Color Tokens
- Backgrounds: `bg-card`, `bg-muted`
- Text: `text-foreground`, `text-muted-foreground`
- Borders: `border` (default)
- Status: green-600/red-600/yellow-600 for semantic indicators
- New: progress bar fills use `bg-primary` (under limit), `bg-yellow-500` (>75%), `bg-red-500` (>90%)

---

## Component 1: GeminiUsageCard

**Location:** Health dashboard page, inserted after HealthStatusCards, before the grid section
**Layout:** Single Card with CardHeader + CardContent

### Structure
```
┌─────────────────────────────────────────────────┐
│ 🤖 Gemini API Usage (Hôm nay)                  │
├─────────────────────────────────────────────────┤
│                                                 │
│ Requests    ███████░░░░░░░░░░░  142 / 1,500    │
│ Tokens      █████████████░░░░░  780K / 1M      │
│                                                 │
│ Breakdown (requests):                           │
│ Technical ·····  42    Fundamental ···  38      │
│ Sentiment ·····  32    Combined ·····  30      │
│                                                 │
│ 7-day trend:                                    │
│ [mini area chart — daily token usage]           │
└─────────────────────────────────────────────────┘
```

### Specs
- **Card**: standard `Card` from shadcn/ui
- **Header**: 14px semibold, icon `Bot` from lucide-react, text "Gemini API Usage (Hôm nay)"
- **Progress bars**: height 8px, rounded-full, background `bg-muted`
  - Fill color: `bg-primary` when <75%, `bg-yellow-500` when 75-90%, `bg-red-500` when >90%
  - Right-aligned label: "142 / 1,500" in 12px regular `text-muted-foreground`
- **Breakdown grid**: 2×2 grid, 12px regular, label + count pairs
- **7-day trend**: Recharts AreaChart, height 48px, no axes, just the filled area. Color follows primary theme.
- **Loading**: `Skeleton` h-48
- **Error**: "Không thể tải Gemini usage." in 12px muted

### Data Source
- Hook: `useGeminiUsage()` → GET `/api/health/gemini-usage?days=7`
- Response: `{ today: { requests, tokens, limit_requests, limit_tokens, breakdown: [...] }, daily: [{ date, tokens, requests }] }`

---

## Component 2: PipelineTimeline

**Location:** Health dashboard page, inserted after the grid section (DataFreshness + DbPool), before ErrorRateChart
**Layout:** Single Card, full width

### Structure
```
┌──────────────────────────────────────────────────────────┐
│ ⏱ Pipeline Timeline (Hôm nay)          [◀ 7 ngày gần đây]│
├──────────────────────────────────────────────────────────┤
│                                                          │
│ 15:30 ▎ Crawl giá       ████████████         │ 45s      │
│ 15:31 ▎ Chỉ báo KT      ██████               │ 22s      │
│ 15:32 ▎ Tin tức          █████████            │ 35s      │
│ 15:33 ▎ Sentiment        ████                 │ 15s      │
│ 15:34 ▎ AI phân tích     ████████████████████ │ 3m 20s   │
│ 15:38 ▎ Kết hợp          ██████████           │ 40s      │
│                                                          │
│ Tổng: 5m 17s                                             │
└──────────────────────────────────────────────────────────┘
```

### Specs
- **Card**: full-width Card
- **Header**: 14px semibold, icon `Timer` from lucide-react, text "Pipeline Timeline"
  - Right side: date selector — today highlighted, 7 buttons for last 7 days, 12px regular
- **Bars**: Recharts horizontal `BarChart` (layout="vertical")
  - Y-axis: job names (Vietnamese labels), 12px regular
  - X-axis: time in seconds, 12px regular
  - Bar color: `bg-primary` (success), `bg-yellow-500` (partial), `bg-red-500` (failed)
  - Bar label (right): formatted duration "45s" or "3m 20s", 12px regular
- **Total**: Bottom line, 12px semibold, "Tổng: 5m 17s"
- **No data state**: "Chưa có dữ liệu pipeline cho ngày này." in 12px muted
- **Loading**: `Skeleton` h-64
- **Date navigation**: shadcn/ui `Button` variant="ghost" size="sm", 7 dates inline

### Data Source
- Hook: `usePipelineTimeline(days)` → GET `/api/health/pipeline-timeline?days=7`
- Response: `{ runs: [{ date, total_seconds, steps: [{ job_id, job_name, started_at, duration_seconds, status }] }] }`

---

## Component 3: Health Alerts (Backend-only)

No new frontend component. Telegram alerts are sent by the backend scheduler job. The existing health page already shows job statuses and data freshness which covers the monitoring UI.

---

## Page Layout Update

Updated health page layout order:
1. Page header (existing)
2. HealthStatusCards (existing)
3. **GeminiUsageCard** (NEW)
4. Grid: DataFreshnessTable + DbPoolStatus + JobTriggerButtons (existing)
5. **PipelineTimeline** (NEW)
6. ErrorRateChart (existing)

---

## Accessibility
- Progress bars: `role="progressbar"`, `aria-valuenow`, `aria-valuemin=0`, `aria-valuemax`
- Timeline bars: labeled by job name
- Color is not the sole indicator — text labels always accompany color coding

## Responsive Behavior
- GeminiUsageCard: single column on mobile, breakdown grid collapses to 1 column
- PipelineTimeline: horizontal scroll on mobile if bars overflow, date selector wraps
