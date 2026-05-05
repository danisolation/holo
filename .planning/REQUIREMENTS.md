# v13.0 Requirements — AI Context & Accuracy

## Goal

Cải thiện chất lượng phân tích AI bằng cách: (1) tích hợp rumor score vào combined analysis, (2) theo dõi accuracy của AI recommendations, (3) thêm volume profile + sector comparison vào Gemini context.

## Requirements

### Rumor-to-Signal Integration

- [ ] **AIUP-01**: Combined analysis prompt includes latest rumor score (credibility, impact, direction) for each ticker alongside technical/fundamental/sentiment
- [ ] **AIUP-02**: Trading signal prompt includes rumor context when available (key claims + direction) to inform entry/SL/TP decisions
- [ ] **AIUP-03**: Daily picks scoring incorporates rumor impact score as a factor (high-impact bullish rumors boost pick ranking)

### AI Accuracy Tracking

- [ ] **ACC-01**: System tracks actual price change (%) at 1-day, 3-day, and 7-day intervals after each AI signal is generated
- [ ] **ACC-02**: Each AI combined recommendation (mua/bán/giữ) gets a binary correct/incorrect verdict based on actual price movement vs direction
- [ ] **ACC-03**: Dashboard shows AI accuracy stats: overall %, per-direction accuracy, rolling 30-day trend
- [ ] **ACC-04**: Accuracy data feeds back into daily picks — tickers where AI has been historically accurate get a confidence boost

### Enhanced Gemini Context

- [ ] **CTX-01**: Technical analysis prompt includes 20-day volume profile (avg volume, volume trend, relative volume vs 20-day avg)
- [ ] **CTX-02**: Combined analysis prompt includes sector peer comparison (ticker's score vs sector average for same analysis type)
- [ ] **CTX-03**: Trading signal prompt includes 52-week price percentile and volume-price correlation

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
| AIUP-01 | Phase 64 | Pending |
| AIUP-02 | Phase 64 | Pending |
| AIUP-03 | Phase 64 | Pending |
| ACC-01 | Phase 65 | Pending |
| ACC-02 | Phase 65 | Pending |
| ACC-03 | Phase 66 | Pending |
| ACC-04 | Phase 66 | Pending |
| CTX-01 | Phase 67 | Pending |
| CTX-02 | Phase 67 | Pending |
| CTX-03 | Phase 67 | Pending |
