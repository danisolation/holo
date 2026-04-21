# Requirements: Holo v5.0 — E2E Testing & Quality Assurance

**Defined:** 2025-07-20
**Core Value:** Dùng Playwright tự động test toàn bộ ứng dụng — phát hiện bug, verify mọi flow E2E, đảm bảo chất lượng.

## v5.0 Requirements

### Test Infrastructure (INFRA)

- [ ] **INFRA-01**: Playwright installed và configured với dual webServer (FastAPI :8001 + Next.js :3000) — cả 2 server tự start/stop khi chạy test
- [x] **INFRA-02**: HOLO_TEST_MODE env guard ngăn scheduler jobs và Telegram bot khởi động khi chạy test
- [x] **INFRA-03**: data-testid attributes trên các component quan trọng (navbar, tabs, forms, tables, charts) để test selector ổn định
- [x] **INFRA-04**: Test helper/fixture tạo seed data (tickers, prices, analysis, paper trades) cho test scenarios
- [ ] **INFRA-05**: .gitignore cập nhật cho test-results/, playwright-report/, screenshots baseline

### Page Smoke Tests (SMOKE)

- [x] **SMOKE-01**: Tất cả 8 routes load thành công không crash: /, /dashboard, /watchlist, /dashboard/paper-trading, /dashboard/portfolio, /dashboard/health, /dashboard/corporate-events, /ticker/[symbol]
- [x] **SMOKE-02**: Navigation giữa các trang hoạt động đúng qua navbar links
- [x] **SMOKE-03**: Các component chính render trên mỗi trang (chart container, data table, cards, tabs)
- [x] **SMOKE-04**: Dark/light theme toggle không break layout

### API Health Checks (API)

- [x] **API-01**: Tất cả API endpoints trả về status code đúng (200/201) và response shape hợp lệ
- [x] **API-02**: Paper trading API endpoints (18 endpoints) respond correctly — CRUD + analytics
- [x] **API-03**: Price, analysis, trading signal endpoints respond với data structure đúng
- [x] **API-04**: Error handling: invalid ticker trả 404, invalid request body trả 422

### User Interaction Tests (INTERACT)

- [x] **INTERACT-01**: Paper trading settings form submit thành công và persist giá trị
- [x] **INTERACT-02**: Trade table sorting (by P&L, status, date) và filtering (by direction, status) hoạt động đúng
- [x] **INTERACT-03**: Watchlist add/remove ticker hoạt động và persist qua page reload
- [x] **INTERACT-04**: Tab switching trên paper trading dashboard (Overview → Trades → Analytics → Calendar → Settings)
- [x] **INTERACT-05**: Ticker detail page tabs và interactive chart controls hoạt động

### Visual Regression (VIS)

- [x] **VIS-01**: Screenshot baseline cho 5 trang chính: Dashboard, Ticker detail, Paper Trading, Portfolio, Watchlist
- [x] **VIS-02**: Chart rendering verification — candlestick chart canvas element tồn tại và có kích thước đúng
- [x] **VIS-03**: Dynamic data areas (prices, timestamps) được mask trong screenshot comparison
- [x] **VIS-04**: Responsive layout test — mobile viewport (375px) không break key pages

### Critical User Flows (FLOW)

- [ ] **FLOW-01**: Flow: Mở ticker → xem analysis → xem trading plan → click Follow → verify paper trade tạo thành công
- [ ] **FLOW-02**: Flow: Mở paper trading dashboard → xem trades → sort/filter → xem analytics tab → xem calendar tab
- [ ] **FLOW-03**: Flow: Thêm ticker vào watchlist → verify hiển thị trên watchlist page → xóa → verify đã xóa
- [ ] **FLOW-04**: Flow: Đổi paper trading settings → verify settings persist → verify ảnh hưởng đến overview

## Future Requirements

### Advanced Testing

- **ADV-01**: Accessibility audit (axe-core) cho tất cả pages
- **ADV-02**: Cross-browser testing (Firefox) ngoài Chromium
- **ADV-03**: Performance profiling — page load time < 3s cho mỗi route
- **ADV-04**: CI/CD pipeline integration (GitHub Actions)

## Out of Scope

| Feature | Reason |
|---------|--------|
| WebSocket real-time testing | 30s polling, market-hours dependent — quá flaky cho automated test |
| Pixel-perfect chart assertions | Canvas-based, data thay đổi daily — chỉ verify existence + dimensions |
| Component unit tests (RTL) | Playwright E2E đủ cho personal project, không cần thêm RTL layer |
| Load/stress testing | Single user app, không cần |
| Mocking entire backend | Test against real servers — mục tiêu là phát hiện real bugs |
| Multi-browser (WebKit) | WebKit không support tốt trên Windows |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| INFRA-01 | Phase 27 | Pending |
| INFRA-02 | Phase 27 | Complete |
| INFRA-03 | Phase 27 | Complete |
| INFRA-04 | Phase 27 | Complete |
| INFRA-05 | Phase 27 | Pending |
| SMOKE-01 | Phase 28 | Complete |
| SMOKE-02 | Phase 28 | Complete |
| SMOKE-03 | Phase 28 | Complete |
| SMOKE-04 | Phase 28 | Complete |
| API-01 | Phase 28 | Complete |
| API-02 | Phase 28 | Complete |
| API-03 | Phase 28 | Complete |
| API-04 | Phase 28 | Complete |
| INTERACT-01 | Phase 29 | Complete |
| INTERACT-02 | Phase 29 | Complete |
| INTERACT-03 | Phase 29 | Complete |
| INTERACT-04 | Phase 29 | Complete |
| INTERACT-05 | Phase 29 | Complete |
| VIS-01 | Phase 30 | Complete |
| VIS-02 | Phase 30 | Complete |
| VIS-03 | Phase 30 | Complete |
| VIS-04 | Phase 30 | Complete |
| FLOW-01 | Phase 31 | Pending |
| FLOW-02 | Phase 31 | Pending |
| FLOW-03 | Phase 31 | Pending |
| FLOW-04 | Phase 31 | Pending |

**Coverage:**
- v5.0 requirements: 26 total
- Mapped to phases: 26
- Unmapped: 0 ✓

---
*Requirements defined: 2025-07-20*
