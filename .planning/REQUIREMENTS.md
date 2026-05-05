# Requirements: Holo — v10.0 Watchlist-Centric & Stock Discovery

**Defined:** 2026-05-04
**Core Value:** AI phân tích đa chiều (kỹ thuật + cơ bản + sentiment) trên dữ liệu chứng khoán Việt Nam real-time để gợi ý trading chính xác và kịp thời qua web dashboard.

## v10.0 Requirements

### Discovery Engine (DISC)

- [x] **DISC-01**: Hệ thống scan ~400 mã HOSE hàng ngày, tính điểm tiềm năng dựa trên kỹ thuật (RSI, MACD, ADX, volume) + cơ bản (P/E, ROE, tăng trưởng)
- [x] **DISC-02**: Kết quả discovery lưu vào DB, giữ lịch sử 14 ngày

### Watchlist Pipeline (WL)

- [x] **WL-01**: AI analysis (Gemini) chỉ chạy trên các mã trong watchlist của user, không phân tích toàn sàn
- [x] **WL-02**: Daily picks chỉ chọn từ các mã trong watchlist

### Discovery Frontend (DPAGE)

- [x] **DPAGE-01**: Trang Discovery hiển thị top mã tiềm năng với điểm số và lý do gợi ý (RSI oversold, MACD cross, volume spike...)
- [x] **DPAGE-02**: User bấm một nút để thêm mã từ Discovery vào watchlist
- [x] **DPAGE-03**: User có thể filter gợi ý theo ngành hoặc loại tín hiệu

### Sector & Heatmap (TAG)

- [x] **TAG-01**: User gán sector/nhóm ngành cho mỗi mã trong watchlist
- [x] **TAG-02**: Khi thêm mã mới, sector tự động gợi ý từ data vnstock (ICB classification)
- [x] **TAG-03**: Heatmap trên trang chủ chỉ hiện các mã trong watchlist, phân nhóm theo sector user đã gán

## Future Requirements

- Discovery score trend (so sánh điểm hôm nay vs hôm qua)
- "New since last check" badge trên Discovery page
- Watchlist-based alerts (notify khi mã trong watchlist có signal mới)

## Out of Scope

| Feature | Reason |
|---------|--------|
| AI-powered discovery (Gemini scan toàn sàn) | 15 RPM rate limit, tốn 200s+ pipeline time — dùng indicator scoring thuần |
| Auto add/remove watchlist | User phải tự quyết định — auto-changes phá trust |
| Custom scoring weights UI | Single user — tune weights trong code nếu cần |
| Multi-user watchlists | Single-user app — không cần auth |
| Watchlist notifications | Telegram bot đã bị xóa v7.0 — check trên web |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| DISC-01 | Phase 52 | Complete |
| DISC-02 | Phase 52 | Complete |
| WL-01 | Phase 53 | Pending |
| WL-02 | Phase 53 | Pending |
| DPAGE-01 | Phase 55 | Pending |
| DPAGE-02 | Phase 55 | Pending |
| DPAGE-03 | Phase 55 | Pending |
| TAG-01 | Phase 54 | Pending |
| TAG-02 | Phase 54 | Pending |
| TAG-03 | Phase 54 | Pending |

**Coverage:**
- v10.0 requirements: 10 total
- Mapped to phases: 10 ✓
- Unmapped: 0

---
*Requirements defined: 2026-05-04*
*Last updated: 2026-05-04 after initial definition*
