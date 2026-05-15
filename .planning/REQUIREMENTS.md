# Requirements: Holo v24.0 Sector Screening & Comparison

**Defined:** 2026-05-15
**Core Value:** Nâng cao tính năng sector — phân loại chi tiết, screener theo ngành, so sánh cổ phiếu cùng ngành, AI peer analysis.

## Milestone Requirements

### Sector Screening

- [ ] **SCRN-01**: User can filter tickers by sector and industry on a dedicated screener page
- [x] **SCRN-02**: User can apply multi-criteria filters (volume, % change, P/E) within a sector
- [x] **SCRN-03**: User can sort screener results by any metric column

### Peer Comparison

- [ ] **PEER-01**: User can view a peer comparison table for tickers in the same sector
- [ ] **PEER-02**: User can see a radar chart comparing a ticker against sector peers on key metrics
- [x] **PEER-03**: Backend provides peer comparison data endpoint with ranked metrics

### Sector Detail

- [ ] **SDET-01**: User can navigate to a sector detail page showing all tickers in that sector
- [ ] **SDET-02**: User can see sector performance chart (7D/30D trend) on the detail page
- [ ] **SDET-03**: Sector detail page links to individual ticker pages

### AI Peer Analysis

- [ ] **AIPEER-01**: Gemini generates peer comparison analysis for a ticker vs its sector peers
- [ ] **AIPEER-02**: AI peer analysis shows relative strengths/weaknesses vs sector average
- [ ] **AIPEER-03**: AI peer analysis is accessible from the ticker detail page

## Traceability

| Requirement | Phase | Plan | Status |
|-------------|-------|------|--------|
| SCRN-01 | Phase 105 | — | Pending |
| SCRN-02 | Phase 104 | — | Pending |
| SCRN-03 | Phase 104 | — | Pending |
| PEER-01 | Phase 105 | — | Pending |
| PEER-02 | Phase 105 | — | Pending |
| PEER-03 | Phase 104 | — | Pending |
| SDET-01 | Phase 105 | — | Pending |
| SDET-02 | Phase 105 | — | Pending |
| SDET-03 | Phase 105 | — | Pending |
| AIPEER-01 | Phase 106 | — | Pending |
| AIPEER-02 | Phase 106 | — | Pending |
| AIPEER-03 | Phase 106 | — | Pending |

## Future Requirements

None deferred.

## Out of Scope

- Real-time intraday sector flow (VCI WS dead) — daily EOD only
- HNX/UPCOM tickers — HOSE only (186 tickers)
- Foreign investor flow tracking — requires paid data source
- Sector-based auto-trade — recommendation only, no auto-execute
