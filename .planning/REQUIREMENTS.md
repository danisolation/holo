# Requirements: Holo v26.0 Dashboard UX & DevOps

**Defined:** 2026-05-16
**Core Value:** Nâng cấp trải nghiệm frontend và thiết lập hệ thống CI/CD + monitoring cho production stability.

## Milestone Requirements

### Dashboard UX

- [ ] **UX-01**: User can toggle dark/light mode và hệ thống nhớ preference across sessions
- [ ] **UX-02**: Dashboard hiển thị đúng trên mobile (responsive layout, touch-friendly navigation)
- [ ] **UX-03**: User thấy trading plan (entry/SL/TP) được vẽ trực tiếp trên candlestick chart dưới dạng price lines
- [ ] **UX-04**: Các trang có loading skeleton và smooth transition khi chuyển route

### DevOps

- [ ] **DEVOPS-01**: Push code trigger tự động: run tests → build → deploy (GitHub Actions)
- [ ] **DEVOPS-02**: User nhận Telegram alert khi backend service down hoặc health check fail
- [ ] **DEVOPS-03**: Hệ thống tự ping và track response time, uptime percentage
- [ ] **DEVOPS-04**: Errors được log tập trung với structured format, dễ query và debug

## Future Requirements

(deferred to future milestones)
- Telegram Bot comeback — trading signal alerts
- AI Portfolio Optimization — auto-rebalance, position sizing
- Backtesting Engine v2

## Out of Scope

- Complex animation library (framer-motion) — use CSS transitions only
- Self-hosted monitoring (Grafana/Prometheus) — overkill for personal use
- Multi-user auth — single user app

## Traceability

| REQ | Phase | Status |
|-----|-------|--------|
| UX-01 | — | Pending |
| UX-02 | — | Pending |
| UX-03 | — | Pending |
| UX-04 | — | Pending |
| DEVOPS-01 | — | Pending |
| DEVOPS-02 | — | Pending |
| DEVOPS-03 | — | Pending |
| DEVOPS-04 | — | Pending |

| Requirement | Phase | Plan | Status |
|-------------|-------|------|--------|
| DUAL-01 | Phase 108 | - | Pending |
| DUAL-02 | Phase 107 | - | Pending |
| DUAL-03 | Phase 107 | - | Pending |
| RAT-01 | Phase 108 | - | Pending |
| RAT-02 | Phase 108 | - | Pending |
| REVIEW-01 | Phase 109 | - | Pending |
| REVIEW-02 | Phase 109 | - | Pending |
| COMP-01 | Phase 109 | - | Pending |
| COMP-02 | Phase 109 | - | Pending |

## Future Requirements

None.

## Out of Scope

None.
