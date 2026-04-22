---
plan: 36-01
phase: 36-frontend-cleanup-utility-extraction
status: complete
started: 2025-07-22
completed: 2025-07-22
---

## Summary

Removed DilutionBadge dead component, extracted duplicated format utilities into shared module, consolidated trade status constants.

## What Was Built

- **Deleted `dilution-badge.tsx`**: Dead component — removed file, import, usage, and entire dilution map logic from holdings-table
- **Created `src/lib/format.ts`**: Shared format utilities (formatVND, formatCompactVND, formatDateVN)
- **Replaced 22 local function definitions** across 18 component files with imports from @/lib/format
- **Created `src/lib/constants.ts`**: TRADE_STATUS_CONFIG consolidating identical configs from bt-trades-tab and pt-trades-table
- **SIGNAL_CONFIG**: Left in analysis-card.tsx — already defined once, contains JSX (React.ReactNode), no duplication

## Metrics

- Files modified: 18 component files
- Files deleted: 1 (dilution-badge.tsx)
- Files created: 2 (format.ts, constants.ts)
- LOC removed: ~124 net (22 duplicate functions removed)
- TypeScript: compiles clean with zero errors
