# Requirements: Holo — Stock Intelligence Platform

**Defined:** 2026-04-15
**Core Value:** AI phân tích đa chiều (kỹ thuật + cơ bản + sentiment) trên dữ liệu HOSE real-time để gợi ý trading chính xác và kịp thời qua Telegram.

## v1 Requirements

Requirements for initial release. Each maps to roadmap phases.

### Data Ingestion

- [ ] **DATA-01**: Crawl dữ liệu giá OHLCV hàng ngày cho 400 mã HOSE nổi bật nhất via vnstock
- [ ] **DATA-02**: Scheduled automated crawling — tự động chạy hàng ngày không cần can thiệp
- [ ] **DATA-03**: Historical data backfill — tải 1-2 năm dữ liệu lịch sử khi khởi tạo
- [ ] **DATA-04**: Crawl báo cáo tài chính (P/E, P/B, doanh thu, lợi nhuận) từ vnstock

### Dashboard & Visualization

- [ ] **DASH-01**: Candlestick charts hiển thị dữ liệu giá OHLCV (lightweight-charts)
- [ ] **DASH-02**: Technical indicator overlays trên charts (MA, RSI, MACD, Bollinger Bands)
- [ ] **DASH-03**: Watchlist — đánh dấu mã yêu thích để theo dõi nhanh
- [ ] **DASH-04**: Ticker detail page — chart + key metrics + AI verdict khi click vào mã
- [ ] **DASH-05**: Responsive layout — dashboard dùng được trên mobile browser
- [ ] **DASH-06**: Market overview / heatmap — cái nhìn tổng quan 400 mã theo sector

### AI Analysis

- [ ] **AI-01**: Technical analysis scoring — RSI, MACD, MA crossovers → tín hiệu bullish/bearish/neutral
- [ ] **AI-02**: Fundamental analysis scoring — P/E, tăng trưởng, sức khỏe tài chính → health score
- [ ] **AI-03**: Sentiment analysis — Gemini phân tích tin tức tiếng Việt → sentiment score
- [ ] **AI-04**: Combined 3-dimensional recommendation — kết hợp kỹ thuật + cơ bản + sentiment → mua/bán/giữ
- [ ] **AI-05**: Confidence level — mức độ tin cậy 1-10 cho mỗi recommendation
- [ ] **AI-06**: Natural language explanation — giải thích recommendation bằng tiếng Việt

### Alerts & Telegram Bot

- [ ] **BOT-01**: Telegram bot gửi trading signal alerts khi AI phát hiện tín hiệu
- [ ] **BOT-02**: Price alert triggers — thông báo khi mã vượt ngưỡng giá do user đặt
- [ ] **BOT-03**: Daily market summary — tóm tắt thị trường sáng/tối qua Telegram

## v2 Requirements

Deferred to future release. Tracked but not in current roadmap.

### Data Quality

- **QUAL-01**: Error handling & retry logic cho crawling failures
- **QUAL-02**: Rate limiting compliance — tuân thủ giới hạn API
- **QUAL-03**: Data gap detection — phát hiện khi thiếu data ngày giao dịch

### Advanced Features

- **ADV-01**: Sector-relative scoring (P/E so với ngành)
- **ADV-02**: AI signal change alerts (chỉ alert khi recommendation thay đổi)
- **ADV-03**: Foreign ownership tracking (room ngoại)
- **ADV-04**: Interactive watchlist qua Telegram (/add, /remove, /list)
- **ADV-05**: On-demand ticker query qua Telegram (/check VNM)
- **ADV-06**: Portfolio tracking với P&L
- **ADV-07**: Stock screener/filter đa tiêu chí
- **ADV-08**: Intraday price tracking trong phiên
- **ADV-09**: Chart image gửi qua Telegram

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| Auto-trading / tự động đặt lệnh | Rủi ro pháp lý và tài chính, chỉ gợi ý |
| Multi-user / authentication phức tạp | Dùng cá nhân, không cần |
| HNX/UPCOM exchanges | Tập trung HOSE trước, mở rộng sau |
| Nguồn dữ liệu trả phí | Dùng vnstock (miễn phí) là đủ |
| Mobile app native | Web responsive + Telegram bot đã cover |
| ML price prediction models | Tạo false confidence, dùng Gemini qualitative analysis |
| Backtesting engine | Phức tạp, dễ sai, là sản phẩm riêng |
| WebSocket real-time streaming | Overkill cho cá nhân, polling 1-5 phút đủ |
| Complex charting editor | TradingView đã có, chỉ cần read-only charts |
| PDF/Excel report export | Dashboard là report, CSV export nếu cần sau |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| DATA-01 | — | Pending |
| DATA-02 | — | Pending |
| DATA-03 | — | Pending |
| DATA-04 | — | Pending |
| DASH-01 | — | Pending |
| DASH-02 | — | Pending |
| DASH-03 | — | Pending |
| DASH-04 | — | Pending |
| DASH-05 | — | Pending |
| DASH-06 | — | Pending |
| AI-01 | — | Pending |
| AI-02 | — | Pending |
| AI-03 | — | Pending |
| AI-04 | — | Pending |
| AI-05 | — | Pending |
| AI-06 | — | Pending |
| BOT-01 | — | Pending |
| BOT-02 | — | Pending |
| BOT-03 | — | Pending |

**Coverage:**
- v1 requirements: 19 total
- Mapped to phases: 0
- Unmapped: 19 ⚠️

---
*Requirements defined: 2026-04-15*
*Last updated: 2026-04-15 after initial definition*
