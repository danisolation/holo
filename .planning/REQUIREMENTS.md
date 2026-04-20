# Requirements: Holo v4.0 — Paper Trading & Signal Verification

**Defined:** 2026-04-20
**Core Value:** Kiểm chứng chất lượng tư vấn AI bằng giả lập trading — mọi signal thành lệnh ảo có thể đo lường.

## v4.0 Requirements

### Paper Trading Engine (PT)

- [x] **PT-01**: Hệ thống tự động tạo paper trade cho mỗi AI trading signal (LONG/BEARISH) với entry/SL/TP từ signal
- [ ] **PT-02**: Paper trade có lifecycle đầy đủ: PENDING → ACTIVE → PARTIAL_TP → CLOSED (TP2/SL/TIMEOUT)
- [ ] **PT-03**: Khi giá chạm TP1, tự động chốt 50% vị thế và dời SL về entry (breakeven)
- [x] **PT-04**: Khi hết timeframe (swing: 15 ngày, position: 60 ngày), tự động đóng lệnh theo giá close
- [ ] **PT-05**: Vốn giả lập tùy chỉnh, position sizing theo AI recommendation, round 100-share lots
- [x] **PT-06**: Scheduler job kiểm tra TP/SL hàng ngày sau khi crawl giá — SL ưu tiên khi cùng bar chạm cả SL và TP
- [ ] **PT-07**: Tính P&L mỗi lệnh (VND + %) bao gồm partial TP — entry tại open ngày D+1 (tránh lookahead bias)
- [x] **PT-08**: Loại bỏ signal score=0 (invalid) khỏi auto-track
- [ ] **PT-09**: User có thể manual follow signal với nút "Follow" — tùy chỉnh entry/SL/TP trước khi mở lệnh ảo

### Core Analytics (AN)

- [ ] **AN-01**: Hiển thị overall win rate (% lệnh thắng trên tổng lệnh đã đóng)
- [ ] **AN-02**: Hiển thị tổng P&L (realized VND + % so với vốn ban đầu)
- [ ] **AN-03**: Equity curve chart — đường cong lợi nhuận tích lũy theo thời gian (Recharts AreaChart)
- [ ] **AN-04**: Max drawdown (% và VND) với drawdown shading trên equity curve
- [ ] **AN-05**: Win rate theo direction (LONG vs BEARISH riêng biệt)
- [ ] **AN-06**: AI score correlation — so sánh hiệu suất theo nhóm confidence (LOW 1-4, MEDIUM 5-7, HIGH 8-10)
- [ ] **AN-07**: Average R:R achieved vs R:R predicted từ signal — đo độ chính xác mục tiêu AI
- [ ] **AN-08**: Profit factor (gross profit / gross loss) và Expected Value per trade
- [ ] **AN-09**: Phân tích theo ngành (sector) — win rate và P&L mỗi ngành, chart bar/table

### Advanced Analytics & UI (UI)

- [ ] **UI-01**: Dashboard page riêng cho paper trading với các tab: Overview, Trades, Analytics, Calendar, Settings
- [ ] **UI-02**: Calendar heatmap (GitHub-style) — xanh ngày thắng, đỏ ngày thua, intensity theo magnitude
- [ ] **UI-03**: Streak tracking — hiển thị chuỗi thắng/thua hiện tại và dài nhất, cảnh báo khi streak thua >5
- [ ] **UI-04**: Phân tích theo timeframe (swing vs position) — so sánh win rate
- [ ] **UI-05**: Signal outcome history trên ticker detail page — 10 signal gần nhất với icon kết quả (✅/❌)
- [ ] **UI-06**: Weekly/monthly performance summary table — win rate, P&L, trade count, avg R:R theo tuần/tháng
- [ ] **UI-07**: Trade list table (sortable, filterable) — symbol, direction, entry, exit, P&L, status, AI score
- [ ] **UI-08**: Settings form — cấu hình vốn ban đầu, auto-track on/off, min confidence threshold

## Future Requirements

### Advanced Features

- **ADV-01**: Fee simulation (0.15% buy + 0.15% sell + 0.1% sell tax) — configurable on/off
- **ADV-02**: Multiple virtual accounts cho A/B testing strategies

## Out of Scope

| Feature | Reason |
|---------|--------|
| Backtesting historical signals | Phức tạp (survivorship bias, lookahead), là sản phẩm riêng — PROJECT.md đã loại |
| Short selling simulation | VN retail không short được — BEARISH track "avoided loss" |
| Slippage/commission simulation | Noise so với TP/SL magnitude (3-10%) — ghi note trên UI |
| Real-time WebSocket paper trade | Swing/position trades không cần intraday check — daily đủ |
| Limit/market order types | Cần tick-by-tick data, overkill cho signal verification |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| PT-01 | Phase 23 | Complete |
| PT-02 | Phase 22 | Pending |
| PT-03 | Phase 22 | Pending |
| PT-04 | Phase 23 | Complete |
| PT-05 | Phase 22 | Pending |
| PT-06 | Phase 23 | Complete |
| PT-07 | Phase 22 | Pending |
| PT-08 | Phase 23 | Complete |
| PT-09 | Phase 24 | Pending |
| AN-01 | Phase 24 | Pending |
| AN-02 | Phase 24 | Pending |
| AN-03 | Phase 24 | Pending |
| AN-04 | Phase 24 | Pending |
| AN-05 | Phase 24 | Pending |
| AN-06 | Phase 24 | Pending |
| AN-07 | Phase 24 | Pending |
| AN-08 | Phase 24 | Pending |
| AN-09 | Phase 24 | Pending |
| UI-01 | Phase 25 | Pending |
| UI-02 | Phase 26 | Pending |
| UI-03 | Phase 26 | Pending |
| UI-04 | Phase 26 | Pending |
| UI-05 | Phase 25 | Pending |
| UI-06 | Phase 26 | Pending |
| UI-07 | Phase 25 | Pending |
| UI-08 | Phase 25 | Pending |

**Coverage:**
- v4.0 requirements: 26 total
- Mapped to phases: 26 ✓
- Unmapped: 0

---
*Requirements defined: 2026-04-20*
*Last updated: 2026-04-20 after initial definition*
