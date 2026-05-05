---
phase: 54-sector-grouping-heatmap-rework
type: validation
---

# Phase 54: Validation Architecture

## Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (backend), manual testing (frontend) |
| Config file | backend/pytest.ini or pyproject.toml |
| Quick run command | `cd backend && python -m pytest tests/ -x -q` |
| Full suite command | `cd backend && python -m pytest tests/ -v` |

## Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| TAG-01 | PATCH /watchlist/{symbol} updates sector_group | unit | `pytest tests/test_watchlist_sector.py -x -k "patch"` | ❌ Wave 0 |
| TAG-01 | GET /watchlist returns sector_group in response | unit | `pytest tests/test_watchlist_sector.py -x -k "get_enriched"` | ❌ Wave 0 |
| TAG-02 | GET /tickers/sectors returns distinct ICB sectors | unit | `pytest tests/test_watchlist_sector.py -x -k "sectors"` | ❌ Wave 0 |
| TAG-02 | POST /watchlist auto-populates sector_group from ICB | unit | `pytest tests/test_watchlist_sector.py -x -k "add_auto_sector"` | ❌ Wave 0 |
| TAG-03 | Heatmap renders only watchlist tickers grouped by sector | manual | Manual browser test | N/A |

## Sampling Rate
- **Per task commit:** Backend unit tests for modified endpoints
- **Per wave merge:** Full backend test suite
- **Phase gate:** All API tests pass + manual heatmap verification

## Wave 0 Gaps
- [ ] Backend test files for new PATCH endpoint and sectors endpoint
- [ ] Frontend manual test checklist for inline editing + heatmap
