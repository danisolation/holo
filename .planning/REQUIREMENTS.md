# Requirements: Holo — v7.0 Consolidation & Quality Upgrade

**Defined:** 2026-04-22
**Core Value:** AI phân tích đa chiều (kỹ thuật + cơ bản + sentiment) trên dữ liệu chứng khoán Việt Nam real-time để gợi ý trading chính xác và kịp thời qua Telegram.

## v7.0 Requirements

### Cleanup — Dead Code Removal (CLN)

- [ ] **CLN-01**: Xóa price_alert model, DB table, và tất cả references (service method, handler import)
- [ ] **CLN-02**: Xóa daily_price.adjusted_close column (migration + model + schema)
- [ ] **CLN-03**: Xóa Financial.revenue và net_profit columns (migration + model)
- [ ] **CLN-04**: Xóa news_article.source column (migration + model)
- [ ] **CLN-05**: Xóa DilutionBadge component (frontend dead code)
- [ ] **CLN-06**: Xóa tất cả formatVND/formatCompactVND/formatDateVN duplicates, extract sang src/lib/format.ts

### Backend Consolidation (BCK)

- [ ] **BCK-01**: Extract shared analytics logic từ backtest_analytics_service + paper_trade_analytics_service thành AnalyticsBase class (win rate, P&L, drawdown, sector, confidence, timeframe)
- [ ] **BCK-02**: Refactor BacktestAnalysisService từ inheritance sang composition pattern — tách AnalysisContextStrategy (Live vs Backtest)
- [ ] **BCK-03**: Gộp BacktestTradeResponse + PaperTradeResponse schemas thành TradeBaseResponse + subclass
- [ ] **BCK-04**: Tách AIAnalysisService (400+ LOC) thành: ContextBuilder, GeminiClient, AnalysisStorage, AnalysisOrchestrator
- [ ] **BCK-05**: Tách BacktestEngine (300+ LOC) thành: BacktestRunner, TradeActivator, PositionEvaluator, EquitySnapshot

### Frontend Consolidation (FRN)

- [ ] **FRN-01**: Tạo GenericTradesTable component thay thế 3 trade tables (portfolio, paper-trading, backtest)
- [ ] **FRN-02**: Tạo shared EquityCurveChart component thay thế pt-equity-chart + bt-analytics equity chart
- [ ] **FRN-03**: Extract STATUS_CONFIG, SIGNAL_CONFIG sang src/lib/constants.ts — xóa duplicates từ tất cả components
- [ ] **FRN-04**: Consolidate watchlist UX — bỏ watchlist cards trên /dashboard, giữ /watchlist page làm single source
- [ ] **FRN-05**: Phân vai rõ "/" (Market Overview — heatmap focus) vs "/dashboard" (Portfolio Dashboard — portfolio focus), bỏ market stats trùng lặp

### AI Quality Upgrade (AIQ)

- [ ] **AIQ-01**: Thêm score-signal consistency validation (score < 5 không được là buy/strong_buy)
- [ ] **AIQ-02**: Thêm price bounds validation cho trading signals (entry within week_52_high/low range)
- [ ] **AIQ-03**: Sanitize news titles trước khi gửi Gemini (strip control chars, enforce max_length)

### Performance Optimization (PRF)

- [ ] **PRF-01**: WebSocket real-time chỉ active trong giờ giao dịch (9:00-15:00 VN weekdays), tự tắt off-hours
- [ ] **PRF-02**: Lazy-load lightweight-charts (150KB) chỉ trên /ticker/[symbol] page, không load global

### Test Maintenance (TST)

- [ ] **TST-01**: Cập nhật unit tests (560 tests) sau khi refactor backend services — đảm bảo tất cả pass
- [ ] **TST-02**: Cập nhật E2E tests (119 tests) sau khi xóa/consolidate frontend components — đảm bảo tất cả pass

## Future Requirements (deferred)

- Complete watchlist migration từ DB sang localStorage (xóa user_watchlist table) — cần update Telegram bot trước
- Multi-source news crawling (thêm nguồn ngoài CafeF)
- Walk-forward optimization — tối ưu tham số AI trên rolling window

## Out of Scope

| Feature | Reason |
|---------|--------|
| Xóa user_watchlist table | Telegram bot vẫn dùng — cần refactor bot trước |
| Thêm feature mới | Milestone này chỉ consolidation + upgrade, không thêm |
| Đổi chart library | lightweight-charts + recharts serve different purposes — chỉ lazy-load |
| Refactor Telegram bot | Scope quá lớn — dành cho milestone riêng |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| CLN-01 | Phase 35 | Pending |
| CLN-02 | Phase 35 | Pending |
| CLN-03 | Phase 35 | Pending |
| CLN-04 | Phase 35 | Pending |
| CLN-05 | Phase 36 | Pending |
| CLN-06 | Phase 36 | Pending |
| BCK-01 | Phase 37 | Pending |
| BCK-02 | Phase 37 | Pending |
| BCK-03 | Phase 37 | Pending |
| BCK-04 | Phase 38 | Pending |
| BCK-05 | Phase 38 | Pending |
| FRN-01 | Phase 40 | Pending |
| FRN-02 | Phase 40 | Pending |
| FRN-03 | Phase 36 | Pending |
| FRN-04 | Phase 40 | Pending |
| FRN-05 | Phase 40 | Pending |
| AIQ-01 | Phase 39 | Pending |
| AIQ-02 | Phase 39 | Pending |
| AIQ-03 | Phase 39 | Pending |
| PRF-01 | Phase 41 | Pending |
| PRF-02 | Phase 41 | Pending |
| TST-01 | Phase 42 | Pending |
| TST-02 | Phase 42 | Pending |

**Coverage:**
- v7.0 requirements: 23 total
- Mapped to phases: 23 ✓
- Unmapped: 0

---
*Requirements defined: 2026-04-22*
*Last updated: 2026-04-22 after initial definition*
