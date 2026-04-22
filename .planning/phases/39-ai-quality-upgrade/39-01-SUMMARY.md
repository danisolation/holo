---
plan: 39-01
phase: 39-ai-quality-upgrade
status: complete
started: 2025-07-22
completed: 2025-07-22
---

## Summary

Added 3 validation layers to AI analysis pipeline.

## Changes

1. **Score-Signal Consistency** (AIQ-01): In `_run_batched_analysis`, after extracting signal/score, reject bullish signals (buy/strong_buy/strong/good/positive/very_positive/mua) when score < 5. Corrected to neutral/giu with warning log.

2. **52-week Price Bounds** (AIQ-02): Extended `_validate_trading_signal` to accept optional week_52_high/low. Entry prices outside range flagged as invalid (score=0). Call site updated to pass context data.

3. **News Title Sanitization** (AIQ-03): Added `_sanitize_title()` in context_builder.py — strips Unicode control characters, collapses whitespace, enforces 300-char limit. Applied to all titles in `get_sentiment_context`.

## Metrics
- Tests: 689 passing (unchanged)
- Files modified: 3 (ai_analysis_service.py, context_builder.py, prompts.py)
