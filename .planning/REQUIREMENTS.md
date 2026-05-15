# Requirements: Holo v23.0 Sector Rotation & Market Breadth

**Defined:** 2026-05-14
**Core Value:** Phân tích dòng tiền ngành và sức khỏe thị trường HOSE — sector heatmap, market breadth, rotation radar, AI sector analysis.

## Milestone Requirements

### Sector Heatmap

- [x] **SHEAT-01**: Dashboard hiển thị heatmap theo sector với % thay đổi giá trung bình ngày (sử dụng Ticker.sector + DailyPrice)
- [x] **SHEAT-02**: Heatmap hỗ trợ chuyển đổi view theo volume (tổng volume ngày theo sector)
- [x] **SHEAT-03**: Click vào sector hiển thị danh sách tickers thuộc sector đó với % change, volume, close price

### Market Breadth

- [x] **MBRD-01**: Backend tính A/D line (Advance/Decline) hàng ngày cho toàn bộ HOSE tickers
- [x] **MBRD-02**: Backend tính % stocks above MA50 và % stocks above MA200 hàng ngày
- [x] **MBRD-03**: Backend tính new 52-week highs vs new 52-week lows hàng ngày
- [ ] **MBRD-04**: Dashboard page hiển thị market breadth charts (A/D line, MA breadth, highs/lows theo thời gian)

### Sector Flow

- [x] **SFLOW-01**: Backend tính net buying/selling volume theo sector hàng ngày (volume × price change direction)
- [ ] **SFLOW-02**: Dashboard hiển thị radar chart so sánh performance 7D vs 30D giữa các sectors
- [x] **SFLOW-03**: Sector ranking table sorted by performance với volume change indicator (tăng/giảm)

### AI Sector Analysis

- [ ] **AISEC-01**: Gemini phân tích sector strong/weak dựa trên breadth data + flow data (structured output)
- [ ] **AISEC-02**: AI đề xuất sector rotation timing — sector nào đang attract/lose money flow
- [ ] **AISEC-03**: Scheduled daily sector analysis chạy sau price crawl (chained trong scheduler)

## Traceability

| Requirement | Phase | Plan | Status |
|-------------|-------|------|--------|
| SHEAT-01 | Phase 101 (BE), Phase 102 (FE) | — | Pending |
| SHEAT-02 | Phase 102 | — | Pending |
| SHEAT-03 | Phase 102 | — | Pending |
| MBRD-01 | Phase 100 | — | Pending |
| MBRD-02 | Phase 100 | — | Pending |
| MBRD-03 | Phase 100 | — | Pending |
| MBRD-04 | Phase 102 | — | Pending |
| SFLOW-01 | Phase 101 | — | Pending |
| SFLOW-02 | Phase 102 | — | Pending |
| SFLOW-03 | Phase 102 | — | Pending |
| AISEC-01 | Phase 103 | — | Pending |
| AISEC-02 | Phase 103 | — | Pending |
| AISEC-03 | Phase 103 | — | Pending |

## Future Requirements

None deferred.

## Out of Scope

- Real-time intraday sector flow (VCI WS dead) — daily EOD only
- HNX/UPCOM tickers — HOSE only (186 tickers)
- Foreign investor flow tracking — requires paid data source
- Sector-based auto-trade — recommendation only, no auto-execute
