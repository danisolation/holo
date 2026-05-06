# Requirements: Holo v15.0 Performance Optimization

**Defined:** 2026-05-06
**Core Value:** AI phân tích đa chiều (kỹ thuật + cơ bản + sentiment + tin đồn) trên dữ liệu chứng khoán Việt Nam real-time để gợi ý trading chính xác và kịp thời qua web dashboard.

## v15.0 Requirements

### Database Performance

- [x] **DB-IDX-01**: Composite indexes trên 7 hot tables (daily_prices, technical_indicators, ai_analyses, daily_picks, weekly_reviews, job_executions, community_posts) cho các query patterns phổ biến
- [ ] **DB-N1-01**: Rumor watchlist summary sử dụng batch aggregate query thay vì per-ticker queries
- [ ] **DB-N1-02**: AI context builder batch-fetch data per dimension thay vì sequential per-ticker queries
- [ ] **DB-PAGE-01**: List endpoints (watchlist, rumor, analysis) có pagination với stable ordering
- [x] **DB-POOL-01**: DB connection pool tuned (pool_size, max_overflow, pool_recycle) cho concurrent jobs + API traffic

### API Caching

- [ ] **CACHE-01**: TTLCache cho expensive read endpoints (sectors, discovery, goals, analysis summary, rumor summary)
- [ ] **CACHE-02**: Dashboard computed payloads cached (latest prices, SMA deltas, volume stats)

### Crawler Efficiency

- [ ] **CRAWL-01**: Crawler fetch phase chạy parallel với bounded concurrency (asyncio.Semaphore)
- [ ] **CRAWL-02**: Bulk multi-row INSERT ON CONFLICT cho rumor/news crawlers thay vì single-row inserts
- [ ] **CRAWL-03**: Centralized ticker map lookup — reuse per job run, không query lại mỗi crawler

### General Performance

- [ ] **PERF-01**: CPU-heavy parsing (BeautifulSoup, DataFrame iterrows) chạy trong asyncio.to_thread()
- [ ] **PERF-02**: Financial service sử dụng bulk upsert thay vì row-by-row

## Future Requirements

None — performance optimization is self-contained.

## Out of Scope

| Feature | Reason |
|---------|--------|
| Redis caching | Overkill for single-user — TTLCache in-memory đủ |
| Read replicas | Single PostgreSQL instance đủ cho personal use |
| CDN/Edge caching | Frontend assets already served by Vercel |
| Query materialized views | Premature — indexes + caching giải quyết trước |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| DB-IDX-01 | Phase 71 | Complete |
| DB-N1-01 | Phase 72 | Pending |
| DB-N1-02 | Phase 72 | Pending |
| DB-PAGE-01 | Phase 72 | Pending |
| DB-POOL-01 | Phase 71 | Complete |
| CACHE-01 | Phase 73 | Pending |
| CACHE-02 | Phase 73 | Pending |
| CRAWL-01 | Phase 74 | Pending |
| CRAWL-02 | Phase 74 | Pending |
| CRAWL-03 | Phase 74 | Pending |
| PERF-01 | Phase 75 | Pending |
| PERF-02 | Phase 75 | Pending |

**Coverage:**
- v15.0 requirements: 12 total
- Mapped to phases: 12 ✓
- Unmapped: 0

---
*Requirements defined: 2026-05-06*
*Last updated: 2026-05-06 after initial definition*
