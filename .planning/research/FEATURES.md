# Feature Landscape — v12.0 Rumor Intelligence

**Domain:** Community rumor crawling & AI scoring for Vietnamese stock market
**Researched:** 2025-07-21

## Table Stakes

Features that make rumor intelligence usable. Missing = feature feels broken.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Fireant community post crawling | Primary data source — no posts, no rumors | Low | JSON API, mirrors CafeFCrawler pattern |
| Post deduplication | Crawling same posts repeatedly wastes storage & AI tokens | Low | ON CONFLICT DO NOTHING on post_id (same as news_articles) |
| AI rumor credibility score (1-10) | Core value prop — raw posts are noise without scoring | Medium | Gemini structured output, new prompt |
| AI impact assessment (1-10) | Users need to know which rumors matter | Medium | Part of same Gemini call |
| Bullish/bearish/neutral classification | Directional signal is fundamental to stock analysis | Low | Single enum field in Gemini response |
| Rumor score on ticker detail page | Must be visible where users look at stocks | Medium | New panel/section on existing page |
| Scheduled automated crawling | Manual triggering is not viable daily | Low | APScheduler job chain, existing pattern |
| Vietnamese explanations | Single-user is Vietnamese speaker | Low | Gemini already outputs Vietnamese |

## Differentiators

Features that add significant value beyond basic functionality.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Rumor feed timeline | See chronological rumor activity per ticker | Medium | New API endpoint + frontend component |
| Watchlist rumor badges | At-a-glance rumor activity on watchlist table | Low | Badge component, query latest rumor score |
| Engagement-weighted scoring | Posts with more likes/replies get higher credibility weight | Low | Pass totalLikes/totalReplies to Gemini prompt |
| Verified user boost | Fireant's `isAuthentic` flag as credibility signal | Low | Include in Gemini context |
| Key claims extraction | AI extracts specific factual claims from rumor noise | Medium | list[str] in Pydantic schema |
| Cross-ticker rumor correlation | Same rumor mentions multiple tickers | High | Deferred — requires post-MVP analysis |
| Historical rumor accuracy tracking | Did past rumors predict price moves? | High | Deferred — needs months of data |

## Anti-Features

Features to explicitly NOT build.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| CafeF forum scraping | Forum is dead (404). URLs removed entirely. | Use Fireant.vn as sole community source |
| Vietnamese NLP preprocessing (underthesea/pyvi) | Gemini handles Vietnamese natively. Tokenization/NER adds complexity with zero benefit for this use case | Send raw Vietnamese text to Gemini |
| Real-time rumor streaming | Overkill for daily analysis cycle. Adds WebSocket complexity | Daily scheduled crawl, same as all other data |
| Rumor notifications via Telegram | Telegram bot removed in v7.0. Web dashboard is primary channel | Show on dashboard, possibly with visual alerts |
| Automated trading based on rumors | Explicitly out of scope (legal/financial risk) | Advisory scores only |
| Multi-source aggregation framework | Over-engineering for 1 source. YAGNI. | Simple FireantCrawler class |
| Sentiment analysis library | spaCy/VADER/etc. are English-focused, heavy, and redundant when Gemini does the analysis | Gemini handles all NLP |

## Feature Dependencies

```
FireantCrawler → community_posts table → RumorScoringService → rumor_scores table
                                                                       ↓
                                                              API endpoints
                                                                       ↓
                                                    Ticker detail page rumor panel
                                                    Watchlist rumor badges
                                                    Rumor feed timeline
```

## MVP Recommendation

Prioritize:
1. Fireant crawling + storage (foundation — everything depends on this)
2. AI rumor scoring with credibility + impact + direction (core value)
3. Rumor panel on ticker detail page (visibility)
4. Watchlist badges (at-a-glance value)

Defer:
- Rumor feed timeline: Nice-to-have, not essential for MVP
- Cross-ticker correlation: Needs data accumulation first
- Historical accuracy tracking: Needs months of scored data
- Key claims extraction: Can be added to prompt later without schema changes if list[str] is included from start

## Sources

- Fireant.vn API: Live tested, response fields documented
- CafeF forum: Verified dead (404) via live testing
- Existing codebase: Feature patterns from v1.0-v11.0
