# Phase 59: UX & Onboarding - Context

**Gathered:** 2026-05-06
**Status:** Ready for planning
**Mode:** Auto-generated (frontend-only UX polish)

<domain>
## Phase Boundary

Improve first-time user experience: preset VN30 watchlist, empty state guidance on key pages, and navigation tooltips describing each section. All frontend-only changes.

</domain>

<decisions>
## Implementation Decisions

### VN30 Preset Watchlist (UX-01)
- When watchlist is empty, show a prominent card/banner with "Thêm VN30 blue-chips" one-click button
- VN30 tickers are hardcoded list (top 30 HOSE by market cap — well-known, rarely changes)
- On click: POST each VN30 ticker to /api/watchlist/ endpoint (batch)
- After adding: refetch watchlist and show populated view

### Empty States (UX-02)
- Heatmap page (page.tsx): Show guidance when no data — "Chưa có dữ liệu. Thêm mã vào danh mục để bắt đầu."
- Watchlist page: Already addressed by VN30 preset — empty state IS the preset prompt
- Discovery page: Show guidance if no discovery results — "Dữ liệu đang được cập nhật..."
- Use existing shadcn/ui Card components for empty state containers
- Include relevant icons (Compass, Star, TrendingUp) for visual appeal

### Navigation Tooltips (UX-03)
- Add `description` field to NAV_LINKS array in navbar.tsx
- Descriptions in Vietnamese:
  - Tổng quan: "Bảng giá & heatmap thị trường"
  - Khám phá: "Gợi ý cổ phiếu từ AI, cập nhật hàng ngày"
  - Danh mục: "Danh mục theo dõi & phân tích AI"
  - Huấn luyện: "AI coach & nhật ký giao dịch"
  - Nhật ký: "Lịch sử giao dịch & hiệu suất"
  - Hệ thống: "Trạng thái hệ thống & API"
- Show as subtitle text below nav label (small muted text) on desktop, or as tooltip on hover

### the agent's Discretion
- Exact VN30 ticker list
- Empty state illustration/icon choices
- Tooltip vs subtitle implementation approach
- Animation/transition details

</decisions>

<code_context>
## Existing Code Insights

### Key Files
- `frontend/src/components/navbar.tsx` — NAV_LINKS array, desktop + mobile nav
- `frontend/src/app/page.tsx` — Home/heatmap page
- `frontend/src/app/watchlist/page.tsx` — Watchlist page
- `frontend/src/app/discovery/page.tsx` — Discovery page
- `frontend/src/components/heatmap.tsx` — Heatmap component
- `frontend/src/components/watchlist-table.tsx` — Watchlist table

### Established Patterns
- shadcn/ui Card, Button components
- Tailwind CSS utility classes
- Vietnamese UI text throughout
- Lucide icons (BarChart3, Search, etc.)
- React Query for data fetching (useWatchlist, useDiscovery hooks)

### Integration Points
- `frontend/src/lib/api.ts` — addToWatchlist function exists
- `frontend/src/lib/hooks.ts` — useWatchlist, useDiscovery hooks

</code_context>

<specifics>
## Specific Ideas

- Keep VN30 list as a constant — these are well-known blue chips
- Empty states should feel helpful, not error-like
- Nav descriptions should be concise (5-8 words max)

</specifics>

<deferred>
## Deferred Ideas

- Interactive onboarding tour/wizard (v12.0+)
- Personalized preset suggestions beyond VN30 (v12.0+)

</deferred>
