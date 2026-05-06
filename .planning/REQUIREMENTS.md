# Requirements: Holo v17.0 AI Consistency & UX

**Defined:** 2026-05-06
**Core Value:** AI phân tích đa chiều (kỹ thuật + cơ bản + sentiment + tin đồn) trên dữ liệu chứng khoán Việt Nam real-time để gợi ý trading chính xác và kịp thời qua web dashboard.

## v17.0 Requirements

### AI Prompt Consistency

- [ ] **APC-01**: Combined analysis recommendation nhất quán với technical signal direction (nếu technical=sell thì combined phải giải thích hoặc đồng thuận, không mâu thuẫn im lặng)
- [ ] **APC-02**: Combined prompt nhận input trực tiếp từ technical/fundamental/sentiment scores và reference chúng trong reasoning
- [ ] **APC-03**: Trading Signal chỉ output 1 hướng recommended (bỏ dual-direction output, chỉ giữ recommended_direction + 1 trading plan)

### Frontend Display

- [ ] **FED-01**: Trading Plan panel chỉ hiện hướng recommended (ẩn hướng thứ yếu)
- [ ] **FED-02**: Analysis cards hiển thị tín hiệu nhất quán — badge/icon đồng bộ với recommendation

### Real-Time Connectivity

- [ ] **RTC-01**: VNDirect WebSocket kết nối được từ Render deployment (fix DNS/network hoặc add fallback mechanism)

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| APC-01 | — | Pending |
| APC-02 | — | Pending |
| APC-03 | — | Pending |
| FED-01 | — | Pending |
| FED-02 | — | Pending |
| RTC-01 | — | Pending |

## Future Requirements

None identified.

## Out of Scope

- Multi-model AI (chỉ dùng Gemini)
- Hoàn toàn bỏ dual analysis (giữ internal logic, chỉ ẩn UI)

## Out of Scope

| Feature | Reason |
|---------|--------|
| Full order book | VNDirect WS only provides top 3 bid/ask levels |
| Price alerts via WebSocket | Existing APScheduler polling alerts sufficient |
| Historical tick data storage | OHLCV daily data already covers analysis needs |
| Multi-exchange real-time | Focus HOSE only — HNX/UPCOM volume too low |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| WS-01 | Phase 76 | Complete |
| WS-02 | Phase 76 | Complete |
| WS-03 | Phase 76 | Complete |
| WS-04 | Phase 76 | Complete |
| BC-01 | Phase 77 | Complete |
| BC-02 | Phase 77 | Complete |
| BC-03 | Phase 77 | Complete |
| FE-01 | Phase 78 | Complete |
| FE-02 | Phase 78 | Complete |
| FE-03 | Phase 79 | Complete |

**Coverage:**
- v15.0 requirements: 12 total
- Mapped to phases: 12 ✓
- Unmapped: 0

---
*Requirements defined: 2026-05-06*
*Last updated: 2026-05-06 after initial definition*
