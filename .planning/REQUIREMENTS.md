# Requirements: Holo v14.0 Multi-Source Rumor & Quota Fix

**Defined:** 2026-05-06
**Core Value:** AI phân tích đa chiều (kỹ thuật + cơ bản + sentiment + tin đồn) trên dữ liệu chứng khoán Việt Nam real-time để gợi ý trading chính xác và kịp thời qua web dashboard.

## v14.0 Requirements

### Quota Fix

- [ ] **QFIX-01**: Gemini rumor scoring sử dụng gemini-2.0-flash thay vì gemini-2.5-flash-lite (1500 RPD free tier)
- [ ] **QFIX-02**: Rumor scoring chạy thành công (>0 tickers scored) khi scheduler trigger

### Multi-Source Crawlers

- [ ] **CRAWL-01**: Crawler VnExpress chứng khoán — lấy tin bài từ vnexpress.net/kinh-doanh/chung-khoan
- [ ] **CRAWL-02**: Crawler Vietstock.vn — lấy tin tức tài chính từ vietstock.vn
- [ ] **CRAWL-03**: Crawler Stockbiz.vn — lấy tin chứng khoán tổng hợp

### Pipeline Integration

- [ ] **PIPE-01**: Tất cả nguồn mới tích hợp vào rumor scoring (Gemini đánh giá combined)
- [ ] **PIPE-02**: Scheduler chain chạy tất cả crawlers (Fireant + F319 + VnExpress + Vietstock + Stockbiz)
- [ ] **PIPE-03**: Rumor prompt phân biệt rõ nguồn (cộng đồng vs tin chính thống vs forum)

## Future Requirements

- **CRAWL-04**: Thêm nguồn TinHoc.vn / CafeF forum nếu cần
- **PIPE-04**: Source reliability weighting (tin chính thống weight > forum)

## Out of Scope

| Feature | Reason |
|---------|--------|
| Full article content extraction | Title + summary đủ cho sentiment; full text tốn token Gemini |
| Paid data sources | Chỉ nguồn miễn phí |
| Real-time news streaming | Daily batch crawl đủ cho personal use |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| QFIX-01 | Phase 68 | Pending |
| QFIX-02 | Phase 68 | Pending |
| CRAWL-01 | Phase 69 | Pending |
| CRAWL-02 | Phase 69 | Pending |
| CRAWL-03 | Phase 69 | Pending |
| PIPE-01 | Phase 70 | Pending |
| PIPE-02 | Phase 70 | Pending |
| PIPE-03 | Phase 70 | Pending |

**Coverage:**
- v14.0 requirements: 8 total
- Mapped to phases: 8 ✓
- Unmapped: 0

---
*Requirements defined: 2026-05-06*
*Last updated: 2026-05-06 after initial definition*

## Future Requirements (Deferred)

- Multi-model consensus (Gemini + Claude/GPT comparison) — cost prohibitive for free tier, defer to v14+
- Real-time intraday signal updates — overkill for EOD analysis cycle
- AI self-reflection / chain-of-thought prompts — experimental, defer

## Out of Scope

- Automated trading based on AI signals — legal/financial risk, advisory only
- Paid Gemini tier optimization — stay on free tier with batch scoring
- Vietnamese NLP for rumor analysis — Gemini handles Vietnamese natively
- ML model training on historical accuracy — insufficient data volume for personal use

## Traceability

| REQ | Phase | Status |
|-----|-------|--------|
| AIUP-01 | Phase 64 | ✅ Done |
| AIUP-02 | Phase 64 | ✅ Done |
| AIUP-03 | Phase 64 | ✅ Done |
| ACC-01 | Phase 65 | ✅ Done |
| ACC-02 | Phase 65 | ✅ Done |
| ACC-03 | Phase 66 | ✅ Done |
| ACC-04 | Phase 66 | ✅ Done |
| CTX-01 | Phase 67 | ✅ Done |
| CTX-02 | Phase 67 | ✅ Done |
| CTX-03 | Phase 67 | ✅ Done |
