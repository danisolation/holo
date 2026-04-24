# Feature Research: v9.0 UX Rework & Simplification

**Domain:** Personal stock trading intelligence tool (single-user, Vietnam HOSE market)
**Researched:** 2025-07-21
**Confidence:** HIGH — based on deep codebase analysis + established trading UX patterns

## Executive Assessment

Holo's core capabilities are strong (AI analysis, daily picks, trade journal, behavior tracking, goals/reviews). The problem isn't missing features — it's **broken flow and scattered layout**. The app has 7 nav items, 3 overlapping market-overview pages, a Coach page that's a kitchen sink (picks + trades + history + goals + behavior all dumped together), and zero connection between recording a trade and what happens next.

The v9.0 UX rework should **not add new features**. It should reorganize existing features into a coherent daily workflow: **See recommendations → Take action → Monitor positions → Review results**. Every screen should answer "what do I do next?"

---

## Current UX Audit (Problems Found in Code)

| Problem | Evidence in Code | Impact |
|---------|-----------------|--------|
| **Overlapping pages** | `/` (heatmap + stats), `/dashboard` (pie chart + top movers) show near-identical market data | User confusion — which one do I use? |
| **Coach page = kitchen sink** | `coach/page.tsx` renders 12+ components: picks, trades, history, goals, weekly review, habits, viewing stats, sector prefs | Overwhelming, can't find what matters |
| **Pick cards are display-only** | `PickCard` has no "Record trade" or "View analysis" buttons, only tracks clicks for behavior | User sees pick → dead end, must navigate elsewhere to act |
| **Trade Journal is isolated** | After `TradeEntryDialog` closes on success, user returns to trade list | No "what to watch for" guidance, no link to AI analysis |
| **Watchlist is localStorage** | `useWatchlistStore` uses zustand persist to `holo-watchlist` key | Loses data on browser clear, no server-side analysis connection |
| **7 nav items** | `NAV_LINKS` in navbar.tsx has 7 entries including 2 to remove | Cognitive overload for single-user tool |
| **No starting point** | Home page is a heatmap — useful for scanning but gives no direction | "I opened the app, now what?" |
| **AI analysis is one paragraph** | `AnalysisCard` renders `analysis.reasoning` as single `<p>` element | User feedback: "too short/terse" |

---

## Feature Landscape

### Table Stakes (Must Fix for v9.0)

These are broken UX patterns that make the app hard to use. Missing = product feels incomplete.

| # | Feature | Why Expected | Complexity | Dependencies |
|---|---------|--------------|------------|--------------|
| T1 | **Action-first home page** | Open app → see what matters today (picks, open positions, market pulse). Not a heatmap. Every trading tool (TradingView, Robinhood, moomoo) leads with "today's relevance." | MEDIUM | Requires reorganizing existing components from coach page + market overview |
| T2 | **"Record trade" button on pick cards** | See AI pick → immediately record trade from the card. Current flow: see pick → mentally note it → navigate to Journal → search ticker → fill form. 4 steps should be 1. | LOW | Reuses existing `TradeEntryDialog` with pre-filled data from pick |
| T3 | **Post-trade next steps** | After recording BUY: show SL/TP levels to watch, link to AI analysis, add to monitoring. After recording SELL: prompt for reflection note. Tradervue, Edgewonk all do this. | MEDIUM | Requires trade creation response to include pick data + new "trade confirmation" UI |
| T4 | **Structured AI analysis output** | AI reasoning should have sections: "Tình hình hiện tại", "Mức hỗ trợ/kháng cự", "Rủi ro", "Kế hoạch hành động". Not a single paragraph. | MEDIUM | Backend AI prompt changes + frontend rendering of structured sections |
| T5 | **Simplified navigation (4 items max)** | Merge overlapping pages. Target: Trang chủ, Phân tích (ticker), Nhật ký, Hệ thống. Remove separate dashboard, watchlist-as-page, coach-as-page. | LOW | Page restructure + redirect handling |
| T6 | **Watchlist to server-side DB** | Watchlist stored in PostgreSQL so it persists. Current localStorage approach is fragile and disconnected from AI pipeline. | LOW | New DB table + API endpoints + migrate zustand store |
| T7 | **Open position monitoring on home** | Show active positions (BUY without matching SELL) with live P&L, proximity to SL/TP. Current coach page shows trades table but without P&L context. | MEDIUM | Combines existing trades data + realtime prices + pick SL/TP data |
| T8 | **Remove corporate events** | Project scope — already decided. Remove backend + frontend + DB. | LOW | Pure deletion |
| T9 | **Remove HNX/UPCOM support** | Project scope — already decided. Only HOSE remains. Remove exchange filter, multi-market code. | LOW-MEDIUM | Backend ticker filtering, frontend ExchangeFilter removal, DB cleanup |

### Differentiators (Set Holo Apart)

Features that aren't expected but make the single-user experience exceptional.

| # | Feature | Value Proposition | Complexity | Dependencies |
|---|---------|-------------------|------------|--------------|
| D1 | **Daily briefing card** | AI-generated 3-5 sentence morning summary: market context, your positions status, today's picks highlight. Not just data — interpretation. Like having a personal analyst say "Here's what matters today." | MEDIUM | New AI prompt for daily summary + backend endpoint |
| D2 | **Trade-to-review loop** | After SELL → prompt "Lý do bán? Bạn đã theo kế hoạch không?" → response feeds into weekly review quality. Closes the learning loop that makes Trade Journal + Weekly Review actually useful together. | MEDIUM | Extends trade creation flow + links to weekly review data |
| D3 | **Contextual coaching on ticker page** | When viewing `/ticker/VNM`, show relevant coaching: "You own this (bought 2025-07-15 at 85,000)" or "AI picked this today" or "Your habit: you tend to sell VNM early." Coaching where you need it, not on a separate page. | MEDIUM | Ticker page enhancement — query trades + picks + habits for current ticker |
| D4 | **Watchlist with AI signals** | Watchlist isn't just a list — each entry shows latest AI score, signal direction, and change since last view. "Your watchlist: VNM ↑ buy 8/10, HPG ↓ neutral 5/10." | LOW | Combines existing API data — watchlist tickers + analysis summary |
| D5 | **Smart trade pre-fill from any context** | From ticker page, from pick card, from watchlist — "Record trade" always pre-fills known data (ticker, suggested price, link to pick). Reduces friction to 2 fields (quantity + date). | LOW | Extend TradeEntryDialog to accept initialData prop |

### Anti-Features (What NOT to Build)

| # | Feature | Why Tempting | Why Problematic | Do This Instead |
|---|---------|-------------|-----------------|-----------------|
| AF1 | **Separate Coach page** | "Coaching" feels like it deserves its own section | Current coach page is a dump of 12 components with no coherent flow. Single-user doesn't need a "coach tab" — coaching should be embedded in context (on home, on ticker page, after trades). | Distribute coach components: picks → home, behavior → settings, goals → home sidebar, weekly review → home |
| AF2 | **Separate Dashboard page** | "Dashboard" sounds important | Current `/dashboard` duplicates `/` (both show market stats). Pie chart + top movers isn't useful daily — heatmap is better. Having two overlapping market views confuses navigation. | Merge into home page. Market pulse section with heatmap + top movers in one view. |
| AF3 | **Heatmap as landing page** | Heatmap looks impressive, shows the whole market | For a personal tool, "what should I do today?" matters more than "what did 400 tickers do?" Heatmap is secondary/exploratory, not the daily starting point. | Heatmap becomes an expandable section on home, or accessed via market pulse area. Today's picks and positions are above the fold. |
| AF4 | **Real-time notification system** | "Alert me when price hits X" | Already removed price alerts in v7. For single-user viewing a web dashboard, real-time price is shown via WebSocket — no need for separate notification layer. Browser tabs are sufficient. | Keep WebSocket price streaming as-is. It's good enough. |
| AF5 | **Customizable dashboard widgets** | "Let user arrange cards" | Single user, single workflow. Customization adds complexity without value — just design the right default layout. | Fixed layout optimized for the daily routine. |
| AF6 | **Gamification (streaks, badges, leaderboards)** | Engagement mechanics from consumer apps | Single user. No one to compete with. Streaks create guilt, not discipline. | Focus on the learning loop: trade → reflect → review → improve. Intrinsic motivation. |
| AF7 | **Chat-with-AI interface** | "Ask the AI about a stock" | Gemini free tier = 15 RPM. Chat would burn through quota fast. Structured analysis is more reliable than free-form chat for trading decisions. | Keep structured AI analysis but make it longer/better. The prompts are the "conversation." |

---

## Feature Dependencies

```
[T8: Remove corporate events]     (independent, do first for cleanup)
[T9: Remove HNX/UPCOM]           (independent, do first for cleanup)
     │
     └─── enables cleaner ───> [T5: Simplified navigation]
                                    │
     ┌──────────────────────────────┘
     │
[T6: Watchlist to DB] ────────> [D4: Watchlist with AI signals]
     │
[T1: Action-first home page] ──requires──> [T5: Simplified navigation]
     │                                          │
     ├── incorporates ──> [T7: Open position monitoring]
     │                          │
     │                          └── enhances ──> [T3: Post-trade next steps]
     │
     └── incorporates ──> [D1: Daily briefing card]
     
[T2: Record trade on pick cards] ──> [T3: Post-trade next steps] ──> [D2: Trade-to-review loop]
     │
     └── enhanced by ──> [D5: Smart trade pre-fill]

[T4: Structured AI analysis] ────────> [D3: Contextual coaching on ticker]
                                              │
                                              └── uses ──> [T6: Watchlist to DB]
```

### Dependency Notes

- **T8+T9 first:** Removing features before reorganizing avoids reworking code that gets deleted. Fewer components to arrange.
- **T5 (navigation) gates T1 (home page):** Can't redesign the landing page without deciding what pages exist.
- **T6 (watchlist DB) gates D4 (smart watchlist):** Can't show AI signals on watchlist without server-side storage to query against.
- **T2 (record from pick) + T3 (post-trade flow) are sequential:** First make it easy to record, then make the post-recording experience useful.
- **T4 (better AI output) gates D3 (contextual coaching):** Richer AI content makes contextual display more valuable.
- **D1 (daily briefing) requires T1 (home page):** The briefing card needs a home to live on.
- **D2 (trade-to-review loop) requires T3 (post-trade flow):** The reflection prompt appears after trade recording.

---

## Proposed User Flow (Daily Routine)

### Morning (Market Open)
```
Open app → Home page
  ├── Daily briefing card: "VN-Index +0.3%, HPG vượt kháng cự..."
  ├── Today's AI picks (3-5 cards with [Ghi lệnh] button)
  ├── Open positions: VNM +2.1% (approaching TP1), FPT -0.5%
  └── Market pulse: heatmap (collapsed/expandable)
```

### During Session
```
Click pick card → [Ghi lệnh] → Pre-filled dialog
  → Submit → "Đã ghi! SL: 82,000 | TP: 92,000 — theo dõi tại đây"
  → Position appears in monitoring section

Click ticker in heatmap → /ticker/VNM
  ├── Chart + indicators (existing)
  ├── Contextual: "Bạn đang giữ 500 cổ VNM (mua 85,000)"
  ├── AI analysis (longer, structured sections)
  └── [Ghi lệnh MUA] or [Ghi lệnh BÁN] button
```

### End of Day / Weekly
```
Record SELL → "Lý do bán? Bạn đã theo kế hoạch không?"
  → Response saved → feeds weekly review

Home page → Weekly review section (when available)
  ├── AI summary of the week
  ├── Good habits / bad habits
  └── Goal progress
```

---

## Navigation Redesign

### Current (7 items, confusing)
```
Tổng quan | Danh mục | Bảng điều khiển | Huấn luyện | Nhật ký | Sự kiện | Hệ thống
```

### Proposed (4 items, clear)
```
Trang chủ | Nhật ký | Thị trường | Hệ thống
```

| New | Content (merged from) | Rationale |
|-----|----------------------|-----------|
| **Trang chủ** | Daily briefing + Today's picks (from Coach) + Open positions (from Coach) + Goals progress (from Coach) + Weekly review (from Coach) + Watchlist quick-view | Everything "today" in one place. The daily starting point. |
| **Nhật ký** | Trade journal (existing) + Trade stats + Behavior insights (from Coach) | "Your trading history and patterns." All backward-looking data. |
| **Thị trường** | Heatmap (from /) + Top movers (from /dashboard) + Market stats | "Explore the market." Scanning tool, not daily landing. |
| **Hệ thống** | Health dashboard (existing, kept for ops) | Admin-only, tucked away. |

**Note:** `/ticker/[symbol]` remains as-is (not a nav item, accessed via search/click). `/watchlist` becomes a section on home page, not a separate page.

---

## MVP Definition (v9.0 Scope)

### Must Have (Launch Blockers)

- [x] **T8: Remove corporate events** — Cleanup before rework
- [x] **T9: Remove HNX/UPCOM** — Cleanup before rework
- [x] **T5: Simplified navigation** — 4 items, merge overlapping pages
- [x] **T1: Action-first home page** — Reorganize existing components into daily routine layout
- [x] **T2: Record trade from pick cards** — Button + pre-filled dialog
- [x] **T6: Watchlist to server-side DB** — Migrate from localStorage
- [x] **T4: Structured AI analysis** — Longer output with sections (prompt engineering + frontend)

### Should Have (High Value, Add Immediately After)

- [ ] **T3: Post-trade next steps** — Confirmation screen with SL/TP + monitoring link
- [ ] **T7: Open position monitoring** — Live P&L on home page
- [ ] **D4: Watchlist with AI signals** — Show score/signal on watchlist entries
- [ ] **D5: Smart trade pre-fill** — Pre-fill from any context (ticker page, watchlist)

### Nice to Have (Future)

- [ ] **D1: Daily briefing card** — AI-generated morning summary (uses Gemini quota)
- [ ] **D2: Trade-to-review loop** — Post-SELL reflection prompt
- [ ] **D3: Contextual coaching on ticker page** — Show position/habit info in context

---

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Risk | Priority |
|---------|-----------|--------------------|----- |----------|
| T8: Remove corporate events | MEDIUM (cleanup) | LOW | LOW | P0 |
| T9: Remove HNX/UPCOM | MEDIUM (cleanup) | LOW-MEDIUM | LOW | P0 |
| T5: Simplified navigation | HIGH | LOW | LOW | P1 |
| T1: Action-first home page | HIGH | MEDIUM | MEDIUM — layout rework | P1 |
| T4: Structured AI analysis | HIGH | MEDIUM | LOW — prompt engineering | P1 |
| T2: Record trade from pick cards | HIGH | LOW | LOW | P1 |
| T6: Watchlist to DB | MEDIUM | LOW | LOW | P1 |
| T7: Open position monitoring | HIGH | MEDIUM | LOW | P2 |
| T3: Post-trade next steps | MEDIUM | MEDIUM | LOW | P2 |
| D4: Watchlist with AI signals | MEDIUM | LOW | LOW | P2 |
| D5: Smart trade pre-fill | MEDIUM | LOW | LOW | P2 |
| D1: Daily briefing card | MEDIUM | MEDIUM | MEDIUM — Gemini quota | P3 |
| D2: Trade-to-review loop | MEDIUM | MEDIUM | LOW | P3 |
| D3: Contextual coaching | MEDIUM | MEDIUM | LOW | P3 |

**Priority key:**
- **P0:** Cleanup — do first to reduce surface area before rework
- **P1:** Core rework — the actual UX transformation
- **P2:** Enhancement — makes the rework shine
- **P3:** Polish — future improvement

---

## Competitor/Pattern Analysis

| UX Pattern | TradingView | Robinhood/moomoo | Tradervue/Edgewonk | Our Approach |
|-----------|-------------|------------------|--------------------|----|
| **Landing page** | Customizable chart workspace | "Today" feed: positions + movers + news | Trade log with stats | **"Today" page:** picks + positions + market pulse |
| **Trade recording** | External (connects to broker) | Automatic from broker | Manual entry with rich tagging | **One-click from pick card**, manual entry in journal |
| **Post-trade flow** | N/A | Shows position in portfolio | Tags, notes, screenshots prompt | **Confirmation with SL/TP reminder**, monitoring link |
| **Watchlist** | Always-visible sidebar panel | Favorites list with live prices | N/A | **Home page section** with AI scores, not separate page |
| **AI/Analysis** | Community scripts + built-in indicators | Simple "analyst ratings" | AI trade grading | **Structured multi-section AI analysis** with clear action guidance |
| **Navigation** | Workspace tabs (flexible) | 5 bottom tabs (Home, Search, Invest, Crypto, Profile) | Simple sidebar (Dashboard, Trades, Reports) | **4 top nav items:** Trang chủ, Nhật ký, Thị trường, Hệ thống |
| **Coaching** | N/A | N/A | Performance reports with habit tracking | **Embedded in context** — on home, ticker page, journal. Not separate page. |

---

## Specific Component Decisions

### Pick Card Redesign
**Current:** Display-only card with price levels. `onClick` only tracks behavior event.
**Proposed:** Add footer with two action buttons:
- `[Ghi lệnh MUA]` — Opens TradeEntryDialog pre-filled with pick data
- `[Xem phân tích →]` — Links to `/ticker/{symbol}`

### Coach Page Decomposition
**Current coach page sections → New locations:**

| Current Section | New Location | Rationale |
|----------------|--------------|-----------|
| Daily Picks (Section 2) | **Home page** — primary content | This IS the daily starting point |
| Performance Cards (Section 1) | **Home page** — above picks | Context for today's picks |
| Open Trades (Section 3) | **Home page** — position monitor | Active monitoring belongs on daily view |
| Pick History (Section 4) | **Nhật ký page** — tab or section | Historical data belongs with journal |
| Goals & Weekly Reviews (Section 5) | **Home page** — sidebar/bottom | Weekly cadence content on the daily view |
| Behavior Insights (Section 6) | **Nhật ký page** — insights tab | Patterns are backward-looking, belong with history |
| Risk Suggestion Banner | **Home page** — top banner | Urgent advisory belongs on the main view |
| Profile Settings | **Home page** — header area or settings | Keep accessible but not prominent |

### AI Analysis Output Structure
**Current:** Single `reasoning` string, typically 2-3 sentences.
**Proposed:** Structured output with sections:

```typescript
interface StructuredAnalysis {
  summary: string;           // 1-2 sentence headline
  market_context: string;    // Overall market + sector context  
  key_levels: string;        // Support/resistance interpretation
  catalysts: string;         // What could move the price
  risks: string;             // What to watch out for
  action_plan: string;       // Concrete "if X then Y" guidance
}
```

**Implementation:** Change Gemini prompt to request structured sections + Pydantic schema for structured output (already using `google-genai` structured output for trading signals). Frontend renders each section with headers and expandable detail.

### Watchlist DB Migration
**Current:** `zustand/persist` → `localStorage('holo-watchlist')` → array of symbol strings.
**Proposed:**
- New `watchlist` table: `id, ticker_symbol, added_at, notes`
- API endpoints: `GET/POST/DELETE /api/watchlist`
- Frontend: Replace `useWatchlistStore` with react-query hooks
- Migration: On first load, check localStorage, POST to API if exists, clear localStorage

---

## UX Principles for v9.0

1. **Every screen answers "what next?"** — No display-only dead ends. Every card has an action button or a link to relevant context.

2. **Morning routine fit** — Home page is designed to be scanned in 2 minutes: picks → positions → market pulse. Everything above the fold.

3. **Record friction < 10 seconds** — From seeing a pick to recording a trade should be: click button → confirm quantity → done. Pre-fill everything possible.

4. **Coach is embedded, not separate** — Coaching advice appears where relevant (ticker page shows your position, home shows your habits), not on a dedicated "coaching" page you have to visit.

5. **Progressive disclosure** — Summary first, detail on demand. AI analysis shows headline + expandable sections. Position shows P&L + expandable SL/TP levels.

---

## Sources & Confidence

| Finding | Basis | Confidence |
|---------|-------|------------|
| Navigation should be ≤5 items | Established UX research (Miller's law, mobile nav patterns). TradingView uses tabs, Robinhood uses 5 bottom nav. | HIGH |
| Action-first home beats heatmap landing | Consumer fintech pattern (Robinhood, Wealthfront all lead with "your stuff" not "the market"). For single user, personal relevance > market overview. | HIGH |
| Pick card needs action buttons | Direct observation: current code has no CTA on pick cards. Every comparable tool (stock screener, signal service) has "trade" or "add to watchlist" buttons. | HIGH |
| Post-trade flow improves journaling | Tradervue and Edgewonk both prompt for notes/tags after trade entry. Research on trading psychology emphasizes the "plan → execute → review" loop. | MEDIUM — based on training data about trading journal apps |
| Structured AI output improves comprehension | Direct user feedback ("AI analysis is too short/terse") + general UX principle that structured content is easier to scan than prose. | HIGH |
| Watchlist should be server-side | Already flagged as "⚠️ Revisit" in PROJECT.md key decisions. localStorage is unreliable for important data. | HIGH |
| Coach page decomposition pattern | UX principle: related actions should be near their context. "Coaching" scattered across home + ticker + journal is more useful than coaching on a separate page. | MEDIUM — opinionated design decision |
| Overlapping page problem | Direct code inspection: `/` page.tsx and `/dashboard` page.tsx both call `useMarketOverview()` and display nearly identical data | HIGH |

---
*Feature research for: Holo v9.0 UX Rework & Simplification*
*Researched: 2025-07-21*
