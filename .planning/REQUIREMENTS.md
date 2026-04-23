# Requirements: Holo — v8.0 AI Trading Coach

**Defined:** 2026-04-23
**Core Value:** AI phân tích đa chiều (kỹ thuật + cơ bản + sentiment) trên dữ liệu chứng khoán Việt Nam real-time để gợi ý trading chính xác và kịp thời qua web dashboard.

## v8.0 Requirements

### Daily Picks (PICK)

- [ ] **PICK-01**: Mỗi ngày app chọn 3-5 mã cụ thể nên mua, dựa trên composite scoring từ AI analysis có sẵn
- [ ] **PICK-02**: Picks được lọc theo vốn (<50M VND) — chỉ gợi ý mã mà user mua được ít nhất 1 lot (100 cổ)
- [ ] **PICK-03**: Picks ưu tiên an toàn — penalize mã có ATR cao (biến động), ADX thấp (không trend), volume thấp (kém thanh khoản)
- [ ] **PICK-04**: Mỗi pick kèm giải thích tiếng Việt (200-300 từ) tại sao chọn mã này, kết hợp phân tích kỹ thuật + cơ bản + sentiment
- [ ] **PICK-05**: Mỗi pick có giá vào cụ thể, mức cắt lỗ (SL), và mức chốt lời (TP) kế thừa từ trading signal pipeline
- [ ] **PICK-06**: Mỗi pick hiển thị position sizing cụ thể: "Mua X cổ × Y đồng = Z VND (N% vốn)"
- [ ] **PICK-07**: Top 5-10 mã "suýt được chọn" kèm 1 câu giải thích tại sao không chọn (chống FOMO)

### Trade Journal (JRNL)

- [x] **JRNL-01**: User nhập lệnh mua/bán thực tế (mã, giá, số lượng, ngày, phí) vào app
- [x] **JRNL-02**: App tự tính P&L theo FIFO, bao gồm phí môi giới (0.15%) và thuế bán (0.1%) theo quy định VN
- [x] **JRNL-03**: Khi log trade, user có thể link đến daily pick tương ứng để theo dõi "có follow AI không?"

### Coach Dashboard (CDSH)

- [x] **CDSH-01**: Trang /coach hiển thị picks hôm nay, trades đang mở, và performance summary trên 1 trang duy nhất
- [x] **CDSH-02**: Lịch sử picks với kết quả thực tế (entry hit?, SL hit?, TP hit?, return sau N ngày) — track TẤT CẢ picks kể cả không trade
- [x] **CDSH-03**: Performance cards: win rate, total P&L, average R:R, streak hiện tại

### Behavior Tracking (BEHV)

- [ ] **BEHV-01**: Ghi nhận mã user xem nhiều nhất, thời điểm xem, tần suất — phát hiện thiên kiến vô thức
- [ ] **BEHV-02**: Phát hiện trading habits: bán sớm khi lãi, giữ lâu khi lỗ, trade impulsive sau tin tức

### Adaptive Strategy (ADPT)

- [ ] **ADPT-01**: Duy trì risk_level (1-5) — sau 3 lần lỗ liên tiếp tự động suggest giảm risk, user confirm trước khi áp dụng
- [ ] **ADPT-02**: Học sector preference từ kết quả trade — bias picks về ngành user thường lãi, giảm ngành thường lỗ

### Goals & Weekly Review (GOAL)

- [ ] **GOAL-01**: User đặt mục tiêu lãi/tháng, app track tiến độ bằng progress bar trên coach dashboard
- [ ] **GOAL-02**: Mỗi tuần app hỏi: "Bạn muốn thận trọng hơn hay mạo hiểm hơn?" — response điều chỉnh risk_level cho tuần sau
- [ ] **GOAL-03**: AI tạo weekly performance review: tóm tắt tuần, highlight thói quen tốt/xấu, gợi ý cải thiện

## Future Requirements (deferred)

- Multi-source news crawling (thêm nguồn ngoài CafeF)
- AI chat / conversational coaching interface
- Intraday / scalping picks (không phù hợp T+2 VN)

## Out of Scope

| Feature | Reason |
|---------|--------|
| Auto-trading / order execution | Rủi ro pháp lý + tài chính, VN brokers không có public trading API cho retail |
| Complex portfolio analytics (Sharpe, beta, correlation) | Overkill cho beginner — simple P&L + win rate là đủ |
| Gamification / badges / XP | Tạo incentive sai — khuyến khích overtrade thay vì kỷ luật |
| Social features / community | Single-user app, social comparison gây FOMO |
| Telegram bot | Đã xóa ở v7.0, web dashboard là primary channel |
| Multi-account / family sharing | Single user, không cần auth |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| PICK-01 | Phase 43 | Pending |
| PICK-02 | Phase 43 | Pending |
| PICK-03 | Phase 43 | Pending |
| PICK-04 | Phase 43 | Pending |
| PICK-05 | Phase 43 | Pending |
| PICK-06 | Phase 43 | Pending |
| PICK-07 | Phase 43 | Pending |
| JRNL-01 | Phase 44 | Complete |
| JRNL-02 | Phase 44 | Complete |
| JRNL-03 | Phase 44 | Complete |
| CDSH-01 | Phase 45 | Complete |
| CDSH-02 | Phase 45 | Complete |
| CDSH-03 | Phase 45 | Complete |
| BEHV-01 | Phase 46 | Pending |
| BEHV-02 | Phase 46 | Pending |
| ADPT-01 | Phase 46 | Pending |
| ADPT-02 | Phase 46 | Pending |
| GOAL-01 | Phase 47 | Pending |
| GOAL-02 | Phase 47 | Pending |
| GOAL-03 | Phase 47 | Pending |

**Coverage:**
- v8.0 requirements: 20 total
- Mapped to phases: 20 ✓
- Unmapped: 0

---
*Requirements defined: 2026-04-23*
*Last updated: 2025-07-24 — traceability updated after roadmap creation*
