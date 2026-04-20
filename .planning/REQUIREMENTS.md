# Requirements: Holo v3.0 Smart Trading Signals

**Defined:** 2026-04-20
**Core Value:** AI phân tích đa chiều (kỹ thuật + cơ bản + sentiment) trên dữ liệu chứng khoán Việt Nam real-time để gợi ý trading chính xác và kịp thời qua Telegram.

## v1 Requirements

Requirements for v3.0 release. Each maps to roadmap phases.

### Signal Foundation

- [x] **SIG-01**: User can view ATR (Average True Range) indicator value for any ticker
- [x] **SIG-02**: User can view ADX (trend strength) indicator value for any ticker
- [x] **SIG-03**: User can view Stochastic oscillator value for any ticker
- [ ] **SIG-04**: User can view support/resistance levels (pivot points) for any ticker
- [ ] **SIG-05**: User can view Fibonacci retracement levels for any ticker

### AI Trading Plan

- [ ] **PLAN-01**: User can view dual-direction analysis (LONG outlook + BEARISH outlook) with confidence per direction
- [ ] **PLAN-02**: User can view specific entry price, stop-loss, and take-profit targets for the recommended direction
- [ ] **PLAN-03**: User can view risk/reward ratio for each trading plan
- [ ] **PLAN-04**: User can view recommended timeframe (swing/position) for each trading plan
- [ ] **PLAN-05**: User can view position sizing suggestion (% of portfolio) for each trading plan
- [ ] **PLAN-06**: User can read Vietnamese explanation of the trading rationale for each direction

### Dashboard Display

- [ ] **DISP-01**: User can view a Trading Plan panel on the ticker detail page showing full LONG and BEARISH analysis
- [ ] **DISP-02**: User can see entry/stop-loss/take-profit price lines overlaid on the candlestick chart

## Future Requirements

### Signal Enhancements

- **SIG-F01**: Chart pattern recognition (head & shoulders, double top/bottom)
- **SIG-F02**: Volume profile analysis for support/resistance confirmation

### Backtesting

- **BT-F01**: User can view historical accuracy of trading signals
- **BT-F02**: User can compare signal performance by timeframe

### Telegram Trading Plans

- **TBOT-F01**: Telegram sends full trading plan with entry/SL/TP in alert messages

## Out of Scope

| Feature | Reason |
|---------|--------|
| Actual short selling execution | VN retail investors cannot short sell on HOSE/HNX/UPCOM |
| Scalp/intraday timeframe | T+2.5 settlement makes day trading impossible on VN exchanges |
| ML price prediction | Creates false confidence; Gemini qualitative analysis preferred |
| Auto-trade execution | Legal and financial risk; advisory only |
| Backtesting engine | Complex standalone product; defer to future milestone |
| Telegram trading plan alerts | Keep Telegram format unchanged this milestone; dashboard-first |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| SIG-01 | Phase 17 | Complete |
| SIG-02 | Phase 17 | Complete |
| SIG-03 | Phase 17 | Complete |
| SIG-04 | Phase 18 | Pending |
| SIG-05 | Phase 18 | Pending |
| PLAN-01 | Phase 19 | Pending |
| PLAN-02 | Phase 19 | Pending |
| PLAN-03 | Phase 19 | Pending |
| PLAN-04 | Phase 19 | Pending |
| PLAN-05 | Phase 19 | Pending |
| PLAN-06 | Phase 19 | Pending |
| DISP-01 | Phase 20 | Pending |
| DISP-02 | Phase 21 | Pending |

**Coverage:**
- v1 requirements: 13 total
- Mapped to phases: 13
- Unmapped: 0 ✓

---
*Requirements defined: 2026-04-20*
*Last updated: 2026-04-20 after initial definition*
