# v12.0 Requirements — Rumor Intelligence

## Goal

Crawl tin đồn từ cộng đồng chứng khoán VN (Fireant.vn), dùng Gemini AI đánh giá độ tin cậy và tác động, hiển thị rumor score riêng biệt trên dashboard.

## Requirements

### Data Crawling

- [x] **RUMOR-01**: User can see community posts from Fireant.vn crawled automatically for watchlist tickers
- [x] **RUMOR-02**: System deduplicates posts on crawl (ON CONFLICT on post_id) and stores in dedicated `rumors` table
- [ ] **RUMOR-03**: Rumor crawl runs automatically as part of daily APScheduler job chain

### AI Scoring

- [x] **RUMOR-04**: Each rumor receives a Gemini AI credibility score (1-10) assessing source reliability and claim plausibility
- [x] **RUMOR-05**: Each rumor receives an impact score (1-10) and bullish/bearish/neutral classification
- [x] **RUMOR-06**: Scoring incorporates engagement metrics (likes, replies) and verified user status as credibility signals
- [x] **RUMOR-07**: AI extracts key factual claims from rumor content as a structured list
- [x] **RUMOR-08**: All AI assessments include Vietnamese explanations

### Frontend Display

- [x] **RUMOR-09**: Ticker detail page shows a rumor score panel with latest credibility and impact scores
- [x] **RUMOR-10**: Ticker detail page shows a chronological rumor feed timeline with scored posts
- [x] **RUMOR-11**: Watchlist table shows rumor badge indicating recent rumor count and overall sentiment

## Future Requirements (Deferred)

- Cross-ticker rumor correlation (same rumor mentions multiple tickers) — needs post-MVP analysis
- Historical rumor accuracy tracking (did rumors predict price moves?) — needs months of scored data
- F319 forum scraping — XenForo HTML scraping, high maintenance, deferred to v13+

## Out of Scope

- CafeF forum scraping — forum is dead (returns 404), dropped entirely
- Vietnamese NLP preprocessing (underthesea/pyvi) — Gemini handles Vietnamese natively
- Real-time rumor streaming — overkill for daily analysis cycle
- Telegram rumor alerts — bot removed in v7.0, web dashboard is primary
- Automated trading based on rumors — legal/financial risk, advisory only
- Multi-source aggregation framework — YAGNI with single source

## Traceability

| REQ | Phase | Status |
|-----|-------|--------|
| RUMOR-01 | Phase 60 | Complete |
| RUMOR-02 | Phase 60 | Complete |
| RUMOR-03 | Phase 63 | Pending |
| RUMOR-04 | Phase 61 | Complete |
| RUMOR-05 | Phase 61 | Complete |
| RUMOR-06 | Phase 61 | Complete |
| RUMOR-07 | Phase 61 | Complete |
| RUMOR-08 | Phase 61 | Complete |
| RUMOR-09 | Phase 62 | Complete |
| RUMOR-10 | Phase 62 | Complete |
| RUMOR-11 | Phase 62 | Complete |
