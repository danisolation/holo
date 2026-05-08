# Requirements: Holo v20.0 Enhanced Price Pipeline

**Defined:** 2026-05-08
**Core Value:** Giá cổ phiếu luôn cập nhật liên tục, lưu trữ vào DB, tự động aggregate thành OHLCV cuối ngày.

## Milestone Requirements

### Real-Time Polling

- [ ] **POLL-01**: VCI price poll interval giảm từ 30s xuống 15s
- [ ] **POLL-02**: Bỏ giới hạn market hours — poll liên tục 24/7 (ngoài giờ dùng giá cuối phiên)
- [ ] **POLL-03**: Poll ALL 400 mã HOSE (không giới hạn watchlist subscribed)

### Lưu Trữ Intraday

- [ ] **STORE-01**: Bảng `intraday_prices` lưu snapshot giá mỗi lần poll (symbol, price, volume, high, low, timestamp)
- [ ] **STORE-02**: Track running high/low trong ngày từ poll data
- [ ] **STORE-03**: Retention policy — tự động xóa intraday data cũ hơn 7 ngày

### Auto-Crawl & Aggregate

- [ ] **AGG-01**: Cuối ngày giao dịch (14:50 UTC+7), aggregate intraday data → daily_prices (OHLCV)
- [ ] **AGG-02**: Sau aggregate, tự động chạy indicator computation cho ngày hôm đó
- [ ] **AGG-03**: Giữ batch crawl (vnstock) làm fallback nếu intraday data không đủ (server downtime)

## Future Requirements

None deferred.

## Out of Scope

- WebSocket streaming real-time (VNDirect WS domain đã chết)
- Tick-by-tick data storage (quá nặng cho DB, 15s interval đủ cho phân tích)
- Real-time indicator computation (chỉ compute indicators cuối ngày)

## Traceability

| REQ-ID | Phase | Status |
|--------|-------|--------|
| POLL-01 | Phase 92 | Pending |
| POLL-02 | Phase 92 | Pending |
| POLL-03 | Phase 92 | Pending |
| STORE-01 | Phase 92 | Pending |
| STORE-02 | Phase 92 | Pending |
| STORE-03 | Phase 93 | Pending |
| AGG-01 | Phase 94 | Pending |
| AGG-02 | Phase 94 | Pending |
| AGG-03 | Phase 94 | Pending |
