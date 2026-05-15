# Requirements: Holo v24.0 Sector Screening & Comparison

**Defined:** 2026-05-15
**Core Value:** Nâng cao tính năng sector — phân loại chi tiết, screener theo ngành, so sánh cổ phiếu cùng ngành, AI peer analysis.

## Milestone Requirements

### Sector Screening

- [ ] **SCRN-01**: User can filter tickers by sector and industry on a dedicated screener page
- [ ] **SCRN-02**: User can apply multi-criteria filters (volume, % change, P/E) within a sector
- [ ] **SCRN-03**: User can sort screener results by any metric column

### Peer Comparison

- [ ] **PEER-01**: User can view a peer comparison table for tickers in the same sector
- [ ] **PEER-02**: User can see a radar chart comparing a ticker against sector peers on key metrics
- [ ] **PEER-03**: Backend provides peer comparison data endpoint with ranked metrics

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
| SCRN-01 | — | — | Pending |
| SCRN-02 | — | — | Pending |
| SCRN-03 | — | — | Pending |
| PEER-01 | — | — | Pending |
| PEER-02 | — | — | Pending |
| PEER-03 | — | — | Pending |
| SDET-01 | — | — | Pending |
| SDET-02 | — | — | Pending |
| SDET-03 | — | — | Pending |
| AIPEER-01 | — | — | Pending |
| AIPEER-02 | — | — | Pending |
| AIPEER-03 | — | — | Pending |

## Future Requirements

None deferred.

## Out of Scope

- Real-time intraday sector flow (VCI WS dead) — daily EOD only
- HNX/UPCOM tickers — HOSE only (186 tickers)
- Foreign investor flow tracking — requires paid data source
- Sector-based auto-trade — recommendation only, no auto-execute
