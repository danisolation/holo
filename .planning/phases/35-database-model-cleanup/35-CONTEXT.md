# Phase 35: Database & Model Cleanup - Context

**Gathered:** 2026-04-22
**Status:** Ready for planning
**Mode:** Auto-generated (infrastructure phase — discuss skipped)

<domain>
## Phase Boundary

All dead database columns and unused tables are removed — the data model reflects only what the system actually uses. Specifically:
- Remove price_alert table entirely (model, service references, handler imports)
- Remove daily_price.adjusted_close column
- Remove Financial.revenue and net_profit columns
- Remove news_article.source column

</domain>

<decisions>
## Implementation Decisions

### the agent's Discretion
All implementation choices are at the agent's discretion — pure infrastructure phase. Use ROADMAP phase goal, success criteria, and codebase conventions to guide decisions. Key considerations:
- Each column/table removal needs an Alembic migration
- Remove all references in models, schemas, services, and API routes
- Ensure no imports break after removal
- Consider batching related migrations vs individual migrations

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- Alembic migration framework already configured (backend/alembic/)
- SQLAlchemy 2.0 async models in backend/app/models/

### Established Patterns
- Models use SQLAlchemy Mapped[] type annotations
- Migrations auto-generated via Alembic
- Services import models from app.models

### Integration Points
- price_alert: telegram/handlers.py (import), telegram/services.py (check_price_alerts)
- daily_price.adjusted_close: app/models/daily_price.py
- Financial.revenue/net_profit: app/models/financial.py
- news_article.source: app/models/news_article.py

</code_context>

<specifics>
## Specific Ideas

No specific requirements — infrastructure phase. Refer to ROADMAP phase description and success criteria.

</specifics>

<deferred>
## Deferred Ideas

None — discuss phase skipped.

</deferred>
