# Requirements: Holo v22.0 Platform Polish & AI Coverage

**Defined:** 2026-05-13
**Core Value:** Nâng cấp toàn diện — mở rộng AI analysis, tăng cường simulator, cải thiện chất lượng code và UX.

## Milestone Requirements

### AI Analysis Coverage

- [ ] **AICOV-01**: Hệ thống tự động chạy AI analysis cho tất cả ticker trong watchlist hàng ngày
- [ ] **AICOV-02**: Schedule auto-analysis vào 8:30 sáng mỗi ngày trading (UTC+7)
- [x] **AICOV-03**: Dashboard hiển thị AI coverage stats (bao nhiêu ticker đã analyze / tổng watchlist)

### Simulator Enhancement

- [ ] **SIM-01**: Auto-sell khi giá hit Stop Loss target (so sánh DailyPrice.close với SL từ trading plan)
- [ ] **SIM-02**: Auto-sell khi giá hit Take Profit target (so sánh DailyPrice.close với TP từ trading plan)
- [ ] **SIM-03**: Portfolio history chart (equity curve — tổng giá trị portfolio theo thời gian)
- [ ] **SIM-04**: P&L timeline (bảng lịch sử giao dịch với running P&L cộng dồn)
- [ ] **SIM-05**: Sell signal integration (AI phát tín hiệu bán/giữ → auto-execute sell cho positions đang mở)

### Data Quality

- [x] **DQ-01**: Fix pre-existing test failures (test_weekly_financial_crawl_calls_service scheduler test)
- [x] **DQ-02**: Thêm unit tests cho simulator service (buy, sell, SL/TP auto-close, fee calculation, FIFO matching)
- [x] **DQ-03**: Thêm unit tests cho pick generation pipeline (signal filter, unified format, date range)
- [x] **DQ-04**: Data integrity checks (phát hiện gaps trong daily_prices, duplicate entries, stale analysis)

### Performance/UX

- [ ] **UX-01**: Loading skeleton states cho tất cả data-fetching pages (watchlist, ticker, simulator, discovery)
- [ ] **UX-02**: Mobile responsive polish (simulator page, discovery page, ticker detail)
- [ ] **UX-03**: Page transition animations (smooth navigation giữa các routes)
- [ ] **UX-04**: Dashboard homepage redesign (key metrics at a glance — portfolio value, AI coverage, recent picks)

## Future Requirements

None deferred.

## Out of Scope

- Real-time intraday trading (chỉ EOD simulator)
- Multi-user authentication
- Telegram bot (web dashboard is primary)
- ML price prediction

## Traceability

| REQ-ID | Phase | Plan | Status |
|--------|-------|------|--------|
| DQ-01 | Phase 96 | — | Pending |
| DQ-02 | Phase 96 | — | Pending |
| DQ-03 | Phase 96 | — | Pending |
| DQ-04 | Phase 96 | — | Pending |
| AICOV-01 | Phase 97 | — | Pending |
| AICOV-02 | Phase 97 | — | Pending |
| AICOV-03 | Phase 97 | — | Pending |
| SIM-01 | Phase 98 | — | Pending |
| SIM-02 | Phase 98 | — | Pending |
| SIM-03 | Phase 98 | — | Pending |
| SIM-04 | Phase 98 | — | Pending |
| SIM-05 | Phase 98 | — | Pending |
| UX-01 | Phase 99 | — | Pending |
| UX-02 | Phase 99 | — | Pending |
| UX-03 | Phase 99 | — | Pending |
| UX-04 | Phase 99 | — | Pending |
