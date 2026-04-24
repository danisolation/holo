---
phase: 50-coach-page-restructure-trade-flow
verified: 2026-04-24T14:56:43Z
status: human_needed
score: 3/3 must-haves verified
overrides_applied: 0
human_verification:
  - test: "Click 'Ghi nhận giao dịch' on a pick card, verify dialog opens pre-filled with ticker (readonly with 'Từ gợi ý AI' badge), entry price, and quantity from the pick"
    expected: "Dialog title says 'Ghi nhận giao dịch từ gợi ý', ticker is readonly, price and quantity are pre-populated"
    why_human: "Visual verification of pre-fill UX and readonly display — cannot confirm rendering correctness via grep"
  - test: "Submit a trade from the pre-filled dialog and verify PostTradeCard appears at top of Picks tab"
    expected: "Green confirmation card shows trade summary (ticker, qty × price), SL/TP monitoring levels, and numbered Vietnamese next steps"
    why_human: "End-to-end flow requires running app with API — state transitions, conditional rendering, and API integration"
  - test: "Click 'Xem nhật ký giao dịch' button on PostTradeCard and verify tab switches to Nhật ký"
    expected: "Active tab changes to Nhật ký, PostTradeCard disappears, journal content is visible"
    why_human: "Tab switching and state cleanup behavior requires live interaction"
  - test: "Verify tab layout: click each tab (Picks, Nhật ký, Mục tiêu) and confirm only that tab's content is visible"
    expected: "Each tab shows its own section — no single long scroll across all sections"
    why_human: "Visual layout verification — TabsContent rendering and content isolation"
---

# Phase 50: Coach Page Restructure & Trade Flow — Verification Report

**Phase Goal:** The Coach page is interactive and action-oriented — user can record trades directly from AI picks with one click and sees clear next steps after every trade
**Verified:** 2026-04-24T14:56:43Z
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Each pick card displays a "Ghi nhận giao dịch" button that opens a trade entry dialog pre-filled with the pick's ticker, entry price, SL, and TP | ✓ VERIFIED | pick-card.tsx L166-178: Button "Ghi nhận giao dịch" with onRecordTrade(pick); page.tsx L74-84: handleRecordTrade builds TradePrefill from pick data (ticker, entry_price, position_size, SL, TP); page.tsx L268-273: TradeEntryDialog rendered with prefill={tradePrefill}; trade-entry-dialog.tsx L170-186: useEffect pre-fills form with ticker, price, quantity, daily_pick_id; L232-241: readonly ticker display with "Từ gợi ý AI" badge |
| 2 | The Coach page uses a tab-based layout (Picks / Nhật ký / Mục tiêu) instead of a single long scroll — each tab loads its own content | ✓ VERIFIED | page.tsx L8: Tabs/TabsList/TabsTrigger/TabsContent imported; L132: controlled Tabs with activeTab state; L134-136: three TabsTrigger (picks/journal/goals); L140-264: three TabsContent with isolated content per tab — Picks has pick cards, Journal has trades+history+behavior, Goals has monthly/weekly |
| 3 | After recording a trade, the app immediately shows the open position with SL/TP monitoring status and clear guidance on what to do next | ✓ VERIFIED | trade-entry-dialog.tsx L205-209: mutation result → onTradeCreated callback; page.tsx L87-100: handleTradeCreated stores {trade, pick} in lastTradeData; page.tsx L143-155: PostTradeCard renders conditionally; post-trade-card.tsx: trade summary (L54-63), SL/TP monitoring (L66-98), "Bước tiếp theo" numbered guidance (L101-124), "Xem nhật ký giao dịch" button (L127-134) |

**Score:** 3/3 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `frontend/src/components/trade-entry-dialog.tsx` | Trade dialog with prefill support | ✓ VERIFIED (535 lines) | TradePrefill interface exported (L68), prefill prop (L81), onTradeCreated callback (L82, L209), readonly ticker display with badge (L232-241), conditional dialog title (L223) |
| `frontend/src/components/pick-card.tsx` | Pick card with trade recording button | ✓ VERIFIED (170 lines) | onRecordTrade optional prop (L15), destructured (L18), "Ghi nhận giao dịch" button (L168-176) with stopPropagation (L171) |
| `frontend/src/components/post-trade-card.tsx` | Post-trade next steps card | ✓ VERIFIED (130 lines) | PostTradeCard exported (L21), trade summary section, SL/TP monitoring (L66-98), "Bước tiếp theo" next steps (L103), "Xem nhật ký giao dịch" button (L127-134), onDismiss/onViewJournal callbacks |
| `frontend/src/app/coach/page.tsx` | Tab-based Coach page with integrated trade flow | ✓ VERIFIED (259 lines) | Tabs with 3 TabsTrigger (L134-136), controlled state (L35), handleRecordTrade (L74), handleTradeCreated (L87), PostTradeCard wiring (L143-155), TradeEntryDialog with prefill (L268-273) |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `coach/page.tsx` | `pick-card.tsx` | `onRecordTrade` prop | ✓ WIRED | page.tsx L201: `onRecordTrade={handleRecordTrade}` → pick-card.tsx L172: `onRecordTrade(pick)` |
| `coach/page.tsx` | `trade-entry-dialog.tsx` | `prefill` prop | ✓ WIRED | page.tsx L271: `prefill={tradePrefill}` → dialog.tsx L170-186: prefill useEffect pre-fills form |
| `coach/page.tsx` | `post-trade-card.tsx` | Conditional render after trade | ✓ WIRED | page.tsx L143-155: `{lastTradeData && (<PostTradeCard .../>)}` with trade+pick data props |
| `trade-entry-dialog.tsx` | `coach/page.tsx` | `onTradeCreated` callback | ✓ WIRED | dialog.tsx L209: `onTradeCreated?.(result)` → page.tsx L272: `onTradeCreated={handleTradeCreated}` |
| `post-trade-card.tsx` | `coach/page.tsx` | `onViewJournal` callback → tab switch | ✓ WIRED | card.tsx L130: `onClick={onViewJournal}` → page.tsx L106-108: `setActiveTab("journal")` |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `pick-card.tsx` | `pick` (DailyPickResponse) | Props from `useDailyPicks()` → `picksData.picks.map()` | Yes — `useDailyPicks` fetches from API `/daily-picks/latest` | ✓ FLOWING |
| `trade-entry-dialog.tsx` | `prefill` (TradePrefill) | Props from `handleRecordTrade(pick)` which maps DailyPickResponse fields | Yes — mapped from real pick data (ticker, entry_price, stop_loss, etc.) | ✓ FLOWING |
| `trade-entry-dialog.tsx` | `result` (TradeResponse) | `mutation.mutateAsync(payload)` → `createTrade()` → `POST /trades` | Yes — `createTrade` returns `Promise<TradeResponse>` via `apiFetch` (api.ts L598-602) | ✓ FLOWING |
| `post-trade-card.tsx` | Props (tickerSymbol, price, stopLoss, etc.) | `lastTradeData.trade` + `lastTradeData.pick` state in page.tsx | Yes — trade from API response, pick from useDailyPicks query data | ✓ FLOWING |
| `coach/page.tsx` | `lastTradeData` | `handleTradeCreated` stores `{trade: TradeResponse, pick: DailyPickResponse}` | Yes — trade from real API mutation, pick matched from query cache | ✓ FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| PostTradeCard module exports | `Select-String "^export function PostTradeCard"` | Found at L21 | ✓ PASS |
| TradePrefill interface exported | `Select-String "^export interface TradePrefill"` | Found at L68 | ✓ PASS |
| TradeEntryDialog module exports | `Select-String "^export function TradeEntryDialog"` | Found at L85 | ✓ PASS |
| PickCard module exports | `Select-String "^export function PickCard"` | Found at L18 | ✓ PASS |
| createTrade returns TradeResponse | `Select-String "createTrade.*Promise<TradeResponse>"` | Found at L598 (api.ts) | ✓ PASS |

Step 7b note: Full end-to-end behavior (click → dialog → submit → PostTradeCard) requires running server. Routed to human verification.

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| FLOW-01 | 50-01, 50-02 | Pick cards có nút "Ghi nhận giao dịch" — 1 click mở trade entry dialog với data pre-filled từ pick | ✓ SATISFIED | "Ghi nhận giao dịch" button in pick-card.tsx L168-176; TradeEntryDialog prefill in page.tsx L268-273 with TradePrefill carrying ticker, price, quantity, pick_id |
| FLOW-02 | 50-02 | Coach page dùng tab-based layout (Picks / Nhật ký / Mục tiêu) thay vì single long scroll | ✓ SATISFIED | Controlled Tabs component in page.tsx L132-264 with three TabsTrigger and three TabsContent sections |
| FLOW-03 | 50-01, 50-02 | Sau khi ghi nhận trade → hiển thị next step rõ ràng (vị thế đang mở, theo dõi SL/TP) | ✓ SATISFIED | PostTradeCard (post-trade-card.tsx) with trade summary, SL/TP monitoring section, "Bước tiếp theo" numbered guidance, "Xem nhật ký giao dịch" navigation |

No orphaned requirements — all 3 IDs (FLOW-01, FLOW-02, FLOW-03) mapped to Phase 50 in REQUIREMENTS.md traceability table are covered.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| None | — | — | — | No real anti-patterns found. All grep hits were false positives: HTML `placeholder` attributes on input fields (trade-entry-dialog.tsx L276/370/394/467/487/532), guard clause `return null` in useMemo (L137), fire-and-forget `.catch(() => {})` for behavior tracking (pick-card.tsx L33). |

### Human Verification Required

### 1. Pre-filled Trade Dialog from Pick Card

**Test:** Click "Ghi nhận giao dịch" on any pick card
**Expected:** Dialog opens with title "Ghi nhận giao dịch từ gợi ý", ticker shown as readonly with "Từ gợi ý AI" badge, price and quantity pre-populated from pick data
**Why human:** Visual rendering of pre-fill UX, readonly ticker display, and badge styling require live app interaction

### 2. Post-Trade Card Appearance

**Test:** Submit a trade from the pre-filled dialog
**Expected:** Green PostTradeCard appears at top of Picks tab showing: trade summary (ticker, qty × price), SL/TP monitoring levels (red for SL, green for TP), numbered Vietnamese next-step guidance ("Bước tiếp theo")
**Why human:** End-to-end flow requires running app with API — state transitions from dialog close → PostTradeCard render

### 3. Journal Tab Switch from PostTradeCard

**Test:** Click "Xem nhật ký giao dịch" button on PostTradeCard
**Expected:** PostTradeCard disappears, active tab switches to "Nhật ký", journal content (open trades, pick history, behavior insights) becomes visible
**Why human:** Tab switching animation and state cleanup (lastTradeData cleared) require live interaction

### 4. Tab Layout Content Isolation

**Test:** Click each tab (Picks, Nhật ký, Mục tiêu) and verify only that tab's content is visible
**Expected:** Picks shows pick cards + performance; Nhật ký shows trades + history + behavior; Mục tiêu shows goals + weekly prompt + review — no single long scroll across all sections
**Why human:** Visual layout verification that TabsContent properly hides/shows sections

### Gaps Summary

No gaps found. All 3 roadmap success criteria are fully verified at the code level:

1. **Pick card → trade dialog flow**: Complete wiring from PickCard `onRecordTrade` → `handleRecordTrade` → TradePrefill state → TradeEntryDialog `prefill` prop → pre-filled form with readonly ticker
2. **Tab-based layout**: Controlled Tabs component with 3 tabs, each with isolated content sections
3. **Post-trade guidance**: Full data flow from TradeEntryDialog `onTradeCreated` → `handleTradeCreated` → lastTradeData state → PostTradeCard rendering with SL/TP + next steps

All 3 requirements (FLOW-01, FLOW-02, FLOW-03) satisfied. Status is `human_needed` because the visual/interactive flow cannot be programmatically confirmed.

---

_Verified: 2026-04-24T14:56:43Z_
_Verifier: the agent (gsd-verifier)_
