# Requirements: Holo v6.0 — AI Backtesting Engine

**Defined:** 2025-07-21
**Core Value:** Backtest hệ thống AI trên dữ liệu lịch sử để kiểm chứng chất lượng tín hiệu trading — so sánh hiệu suất AI vs VN-Index.

## v6.0 Requirements

### Backtest Engine Core (BT)

- [ ] **BT-01**: User can chọn khoảng thời gian backtest (1-6 tháng, mặc định 6 tháng / 120 phiên)
- [ ] **BT-02**: Hệ thống duyệt từng phiên giao dịch lịch sử, gọi Gemini AI phân tích technical + combined + trading signal tại mỗi phiên
- [ ] **BT-03**: Hệ thống tự động mở lệnh ảo khi có tín hiệu AI (theo direction, entry price, SL/TP từ trading plan)
- [ ] **BT-04**: Hệ thống theo dõi và đóng lệnh ảo theo SL/TP/timeout tại mỗi phiên tiếp theo
- [ ] **BT-05**: Backtest có checkpoint/resume — lưu tiến trình, có thể tiếp tục nếu bị gián đoạn (crash, rate limit)
- [ ] **BT-06**: Backtest chạy trên toàn bộ 400+ mã với smart batching tránh Gemini rate limit (15 RPM)

### Portfolio Simulation (SIM)

- [ ] **SIM-01**: User can cấu hình vốn khởi điểm (mặc định 100M VND)
- [ ] **SIM-02**: Position sizing theo % vốn hiện tại, tái sử dụng logic paper trading v4.0
- [ ] **SIM-03**: Slippage simulation — giả lập trượt giá khi mở/đóng lệnh (configurable %)
- [ ] **SIM-04**: Equity tracking theo từng phiên — số dư, vị thế mở, P&L tích lũy, % return

### Analytics & Benchmark (BENCH)

- [ ] **BENCH-01**: So sánh equity curve AI strategy vs VN-Index buy-and-hold trong cùng khoảng thời gian
- [ ] **BENCH-02**: Tính toán và hiển thị: win rate, total P&L, max drawdown, Sharpe ratio
- [ ] **BENCH-03**: Thống kê hiệu suất AI theo ngành (ngành nào AI phân tích chính xác nhất)
- [ ] **BENCH-04**: Thống kê theo confidence level — confidence cao có tỷ lệ thắng cao hơn không
- [ ] **BENCH-05**: Thống kê theo timeframe — AI phân tích ngắn hạn hay trung hạn chính xác hơn

### Dashboard UI (DASH)

- [ ] **DASH-01**: Trang /backtest với form cấu hình (thời gian, vốn, slippage) và nút "Run Backtest"
- [ ] **DASH-02**: Progress bar real-time hiển thị tiến trình backtest đang chạy (% hoàn thành, ETA)
- [ ] **DASH-03**: Equity curve chart (Recharts area chart) — AI vs VN-Index overlay so sánh trực quan
- [ ] **DASH-04**: Bảng thống kê tổng hợp — win rate, total P&L, max drawdown, Sharpe ratio, số lệnh
- [ ] **DASH-05**: Bảng chi tiết từng lệnh — symbol, direction, entry/exit price, P&L, holding time
- [ ] **DASH-06**: Charts breakdown theo ngành, confidence level, timeframe (bar/pie charts)

## Future Requirements (deferred)

- Telegram backtest notification — bỏ theo yêu cầu user
- Multi-strategy comparison — so sánh nhiều chiến lược AI khác nhau
- Walk-forward optimization — tối ưu tham số AI trên rolling window
- Monte Carlo simulation — stress test portfolio scenarios

## Out of Scope

- **Auto-trade**: Không tự động giao dịch thật — chỉ mô phỏng ảo
- **Real-time backtest**: Không chạy backtest trong giờ giao dịch — chỉ dữ liệu lịch sử
- **Custom AI models**: Không thay đổi Gemini model — dùng model hiện tại (gemini-2.5-flash-lite)
- **Telegram notifications**: Bỏ hoàn toàn — chỉ xem kết quả trên web dashboard

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| BT-01 | Phase 32 | Pending |
| BT-02 | Phase 32 | Pending |
| BT-03 | Phase 32 | Pending |
| BT-04 | Phase 32 | Pending |
| BT-05 | Phase 32 | Pending |
| BT-06 | Phase 32 | Pending |
| SIM-01 | Phase 32 | Pending |
| SIM-02 | Phase 32 | Pending |
| SIM-03 | Phase 32 | Pending |
| SIM-04 | Phase 32 | Pending |
| BENCH-01 | Phase 33 | Pending |
| BENCH-02 | Phase 33 | Pending |
| BENCH-03 | Phase 33 | Pending |
| BENCH-04 | Phase 33 | Pending |
| BENCH-05 | Phase 33 | Pending |
| DASH-01 | Phase 34 | Pending |
| DASH-02 | Phase 34 | Pending |
| DASH-03 | Phase 34 | Pending |
| DASH-04 | Phase 34 | Pending |
| DASH-05 | Phase 34 | Pending |
| DASH-06 | Phase 34 | Pending |

**Coverage:**
- v6.0 requirements: 21 total
- Mapped to phases: 21
- Unmapped: 0 ✓

---
*Requirements defined: 2025-07-21*
