# Requirements: Holo v19.0 Unified AI Analysis Pipeline

**Defined:** 2026-05-07
**Core Value:** AI phân tích đa chiều trên dữ liệu chứng khoán Việt Nam — unified pipeline cho ra 1 kết quả đồng nhất, không mâu thuẫn.

## Milestone Requirements

### Backend — Unified Pipeline

- [ ] **UNIFY-01**: Unified prompt gửi ALL context (indicators, financials, news, rumors) ra 1 JSON response chứa: signal (mua/bán/giữ), score (1-10), entry price, stop-loss, take-profit, reasoning
- [ ] **UNIFY-02**: Xóa analysis types cũ: technical, fundamental, sentiment, combined, trading_signal — cả model, service code, và scheduled jobs
- [ ] **UNIFY-03**: Scheduler chạy 1 unified analysis job thay vì 5 jobs riêng lẻ
- [ ] **UNIFY-04**: API endpoints trả về unified analysis result thay vì multi-type responses

### Backend — Data Cleanup

- [ ] **CLEAN-01**: Migration xóa data cũ của 5 analysis types khỏi ai_analyses table
- [ ] **CLEAN-02**: Simplify ai_analyses schema — bỏ fields thừa, thêm entry_price/stop_loss/take_profit columns

### Frontend — Ticker Redesign

- [ ] **FE-01**: Redesign ticker detail page: 1 panel AI analysis duy nhất (bỏ tabs Technical/Fundamental/Sentiment/Combined)
- [ ] **FE-02**: Panel hiển thị: signal badge, score, entry/SL/TP, key levels, full reasoning
- [ ] **FE-03**: Market overview & watchlist cards show unified signal instead of multi-type

### Prompt Quality

- [ ] **PROMPT-01**: Prompt mới phải include: current price context, all indicators, financials summary, recent news, rumor scores — trong 1 structured input
- [ ] **PROMPT-02**: Output validation: entry ±5% current price, SL ≤3×ATR, TP ≤5×ATR (keep existing rules)

## Future Requirements

None deferred.

## Out of Scope

- Auto-trading execution — chỉ gợi ý, không tự giao dịch
- Multiple AI models comparison — chỉ dùng Gemini
- Historical analysis replay — focus on current pipeline

## Traceability

| REQ-ID | Phase | Status |
|--------|-------|--------|
| UNIFY-01 | TBD | Pending |
| UNIFY-02 | TBD | Pending |
| UNIFY-03 | TBD | Pending |
| UNIFY-04 | TBD | Pending |
| CLEAN-01 | TBD | Pending |
| CLEAN-02 | TBD | Pending |
| FE-01 | TBD | Pending |
| FE-02 | TBD | Pending |
| FE-03 | TBD | Pending |
| PROMPT-01 | TBD | Pending |
| PROMPT-02 | TBD | Pending |
