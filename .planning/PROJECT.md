# Holo — Stock Intelligence Platform

## What This Is

Ứng dụng crawl dữ liệu chứng khoán sàn HOSE cho 400 mã nổi bật nhất, kết hợp AI (Google Gemini) để phân tích kỹ thuật, cơ bản và sentiment — đưa ra gợi ý trading qua web dashboard và Telegram bot. Dành cho sử dụng cá nhân.

## Core Value

AI phân tích đa chiều (kỹ thuật + cơ bản + sentiment) trên dữ liệu HOSE real-time để gợi ý trading chính xác và kịp thời qua Telegram.

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] Crawl dữ liệu giá OHLCV 400 mã HOSE từ VNDirect/SSI API
- [ ] Crawl báo cáo tài chính (doanh thu, lợi nhuận, P/E, P/B...) từ VNDirect/CafeF
- [ ] Crawl tin tức & sự kiện liên quan đến các mã chứng khoán
- [ ] Lưu trữ dữ liệu lịch sử trong PostgreSQL (Aiven)
- [ ] Scheduled crawl tự động hàng ngày
- [ ] Real-time price tracking trong phiên giao dịch
- [ ] AI phân tích kỹ thuật (MA, RSI, MACD, Bollinger Bands...)
- [ ] AI phân tích cơ bản (P/E, tăng trưởng, sức khỏe tài chính...)
- [ ] AI phân tích sentiment từ tin tức
- [ ] AI tổng hợp 3 chiều → gợi ý mua/bán/giữ
- [ ] Web dashboard hiển thị data, biểu đồ, gợi ý AI
- [ ] Telegram bot gửi alert khi có tín hiệu trading
- [ ] Dashboard cá nhân: watchlist, portfolio tracking

### Out of Scope

- Tự động giao dịch (auto-trade) — rủi ro pháp lý và tài chính, chỉ gợi ý
- Mobile app — web-first, responsive là đủ cho cá nhân
- Multi-user / authentication phức tạp — chỉ một người dùng
- Dữ liệu sàn HNX/UPCOM — tập trung HOSE trước
- Nguồn dữ liệu trả phí (FireAnt Pro, Entrade) — dùng nguồn miễn phí

## Context

- **Sàn HOSE:** Sàn giao dịch chứng khoán TP.HCM — sàn lớn nhất Việt Nam
- **400 mã:** Bao gồm VN30, VN100 và các mã có thanh khoản cao nhất
- **Nguồn dữ liệu miễn phí:** VNDirect API, SSI API, CafeF scraping
- **Phiên giao dịch HOSE:** 9:00-11:30 sáng, 13:00-14:45 chiều (giờ VN, UTC+7)
- **Người dùng đã có:** Gemini API key, PostgreSQL Aiven URL
- **Mục đích:** Hỗ trợ quyết định đầu tư cá nhân, không phải sản phẩm thương mại

## Constraints

- **AI Model**: Google Gemini — người dùng đã có API key
- **Database**: PostgreSQL trên Aiven — đã có connection URL
- **Backend**: Python (FastAPI) — mạnh cho data processing & AI
- **Frontend**: React / Next.js — dashboard interactivity
- **Bot**: Telegram Bot API — kênh thông báo chính
- **Data Sources**: Chỉ nguồn miễn phí (VNDirect API, SSI API, CafeF)
- **Scope**: Dùng cá nhân — không cần auth phức tạp hay multi-tenancy

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Gemini cho AI analysis | User đã có API key, chi phí hợp lý | — Pending |
| PostgreSQL Aiven cho DB | User đã có sẵn, managed service không cần ops | — Pending |
| Chỉ crawl nguồn miễn phí | Giảm chi phí, đủ dữ liệu cho phân tích cá nhân | — Pending |
| FastAPI + Next.js | Python mạnh data/AI, Next.js mạnh dashboard UI | — Pending |
| Telegram bot cho alerts | Nhận thông báo mọi lúc trên điện thoại | — Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-04-15 after initialization*
