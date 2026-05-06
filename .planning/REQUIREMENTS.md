# Requirements: Holo v18.0 Multi-Source Community Rumors

**Defined:** 2026-05-06
**Core Value:** AI phân tích đa chiều (kỹ thuật + cơ bản + sentiment + tin đồn đa nguồn) trên dữ liệu chứng khoán Việt Nam real-time để gợi ý trading chính xác và kịp thời qua web dashboard.

## v18.0 Requirements

### Telegram Channel Monitoring

- [ ] **TGM-01**: Crawl public VN stock Telegram channels (Telethon MTProto) và extract ticker mentions vào rumors table
- [ ] **TGM-02**: Config-driven channel list (env var) + feature flag để enable/disable
- [ ] **TGM-03**: APScheduler job chạy mỗi 30 phút (market hours) để backfill messages mới

### News Source Expansion

- [ ] **NSE-01**: Crawler tinnhanhchungkhoan.vn — scrape article listings, extract tickers, store vào news/rumors table
- [ ] **NSE-02**: F319 second RSS feed (giao-lưu forum) — mở rộng f319_crawler hiện tại
- [ ] **NSE-03**: nhadautu.vn crawler (nếu có RSS/crawlable)

### AI Rumor Intelligence

- [ ] **ARI-01**: Rumor scoring aggregate từ tất cả nguồn với source weighting (Fireant > F319 > Telegram > tinnhanhchungkhoan)
- [ ] **ARI-02**: Source credibility scoring — weight higher cho nguồn uy tín, penalize pump-and-dump patterns
- [ ] **ARI-03**: Cross-source corroboration — nếu ≥2 nguồn đề cập cùng ticker + direction → boost confidence

### Frontend Display

- [ ] **FRD-01**: Dashboard rumor panel hiển thị source tag (Fireant/F319/Telegram/TNCK) + icon cho mỗi nguồn

## Traceability

| REQ-ID | Phase | Status |
|--------|-------|--------|
| TGM-01 | TBD | Pending |
| TGM-02 | TBD | Pending |
| TGM-03 | TBD | Pending |
| NSE-01 | TBD | Pending |
| NSE-02 | TBD | Pending |
| NSE-03 | TBD | Pending |
| ARI-01 | TBD | Pending |
| ARI-02 | TBD | Pending |
| ARI-03 | TBD | Pending |
| FRD-01 | TBD | Pending |

## Out of Scope

- StockTraders.vn (paid login wall, no public content)
- Facebook groups (aggressive bot blocking, login required)
- Multi-model AI (chỉ dùng Gemini)

---
*Requirements defined: 2026-05-06*
