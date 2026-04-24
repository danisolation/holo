# Requirements: Holo — v9.0 UX Rework & Simplification

**Defined:** 2026-04-24
**Core Value:** AI phân tích đa chiều (kỹ thuật + cơ bản + sentiment) trên dữ liệu chứng khoán Việt Nam real-time để gợi ý trading chính xác và kịp thời qua web dashboard.

## v9.0 Requirements

### Cleanup — Feature Removal (CLN)

- [ ] **CLN-01**: Xóa toàn bộ tính năng corporate events (DB tables, API endpoints, scheduler jobs, frontend pages)
- [ ] **CLN-02**: Xóa hỗ trợ sàn HNX & UPCOM (chỉ giữ HOSE), rewire scheduler chain an toàn từ UPCOM→HOSE trigger
- [ ] **CLN-03**: Xóa python-telegram-bot khỏi requirements.txt (dead dependency từ v7.0)

### Navigation & Watchlist (NAV)

- [ ] **NAV-01**: Giảm navigation từ 7 items xuống 4-5 items, gộp các trang có nội dung trùng lặp
- [ ] **NAV-02**: Migrate watchlist từ localStorage sang PostgreSQL (Alembic migration + REST API + React Query hooks)
- [ ] **NAV-03**: Watchlist hiển thị AI signal score/recommendation bên cạnh mỗi mã trong danh sách

### Coach & Trade Flow (FLOW)

- [ ] **FLOW-01**: Pick cards có nút "Ghi nhận giao dịch" — 1 click mở trade entry dialog với data pre-filled từ pick
- [ ] **FLOW-02**: Coach page dùng tab-based layout (Picks / Nhật ký / Mục tiêu) thay vì single long scroll
- [ ] **FLOW-03**: Sau khi ghi nhận trade → hiển thị next step rõ ràng (vị thế đang mở, theo dõi SL/TP)

### AI Analysis Improvement (AI)

- [ ] **AI-01**: AI analysis output dài hơn với sections rõ ràng (tóm tắt, mức giá quan trọng, rủi ro, hành động cụ thể)
- [ ] **AI-02**: Giảm batch size + tăng token/thinking limits cho output chất lượng hơn (prompt engineering)
- [ ] **AI-03**: Frontend render AI output dạng structured sections với headings thay vì plain text block

## Future Requirements

- Watchlist-based alerts (notify khi mã trong watchlist có signal mới)
- Open position monitoring dashboard (realtime SL/TP tracking)
- Post-trade AI guidance (gợi ý hành động tiếp theo cho vị thế đang mở)

## Out of Scope

- Multi-user / authentication — vẫn single-user
- Mobile native app — web responsive đủ
- Re-add Telegram bot — web dashboard là kênh chính
- Re-add HNX/UPCOM — giữ focus HOSE cho đơn giản

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| CLN-01 | — | Pending |
| CLN-02 | — | Pending |
| CLN-03 | — | Pending |
| NAV-01 | — | Pending |
| NAV-02 | — | Pending |
| NAV-03 | — | Pending |
| FLOW-01 | — | Pending |
| FLOW-02 | — | Pending |
| FLOW-03 | — | Pending |
| AI-01 | — | Pending |
| AI-02 | — | Pending |
| AI-03 | — | Pending |

---
*Requirements defined: 2026-04-24*
