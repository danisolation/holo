# Research Summary: v3.0 Smart Trading Signals

**Domain:** AI-powered trading signal generation with dual-direction analysis
**Researched:** 2026-04-20
**Overall confidence:** HIGH

## Executive Summary

The v3.0 Smart Trading Signals milestone transforms Holo's AI output from simple mua/bán/giữ recommendations into full trading plans with dual-direction LONG/SHORT analysis, concrete entry/SL/TP price levels, risk-reward ratios, position sizing, and timeframe recommendations. The key finding is that **zero new dependencies are needed** — the existing stack (google-genai structured output, ta library indicators, lightweight-charts, shadcn/ui) covers every technical requirement.

The Gemini structured output capability is the cornerstone. Verified that `google-genai >=1.73` accepts nested Pydantic models (3 levels deep: batch → ticker signal → direction analysis → trading plan detail) as `response_schema`, and returns fully validated instances via `response.parsed`. This means the trading plan schema enforces correct enums (Direction, Timeframe), constrained ranges (confidence 1-10, position size 1-100%), and type safety on all price fields — exactly matching the existing pattern for technical/fundamental/sentiment/combined analyses.

The `ta==0.11.0` library already contains ATR (stop-loss distance), ADX (trend strength), and Stochastic (overbought/oversold) — three indicators that significantly enhance trading signal context. They've been unused because previous analyses only needed close-price indicators. The `DailyPrice` model already stores OHLCV data, so these indicators require no new data sources. Support/resistance levels use pivot points and Fibonacci retracements — pure arithmetic on OHLC data with no library dependency.

Token budget impact is the primary constraint to manage. Adding trading signals as a 5th analysis type increases daily API calls from ~128 to ~160 (within 1,500 RPD free tier) but increases per-batch output tokens ~5x due to the detailed dual-direction plans. Mitigation: reduce batch size from 25 to 15 tickers for this analysis type. The pipeline adds ~4 minutes to the daily schedule — well within acceptable bounds.

## Key Findings

**Stack:** Zero new dependencies. google-genai nested Pydantic structured output + ta library ATR/ADX/Stochastic + lightweight-charts price lines + shadcn/ui Cards handle everything.

**Architecture:** New `TRADING_SIGNAL` analysis type chains as 5th step after combined analysis. Trading plan details stored in existing `ai_analyses.raw_response` JSONB column. Three new indicator columns (ATR, ADX, Stochastic) added to `technical_indicators` table.

**Critical pitfall:** Gemini generating unrealistic price targets (SL below Bollinger lower, TP above 52-week high) — mitigate by feeding pivot/Fibonacci/ATR context in prompt so Gemini anchors to real price structure, plus Pydantic post-validation on the backend.

## Implications for Roadmap

Based on research, suggested phase structure:

1. **Phase 1: Enhanced Indicators** — Add ATR, ADX, Stochastic computation to indicator_service + DB migration
   - Addresses: Foundation data for all trading signal features
   - Avoids: Building signals without proper indicator context (Pitfall: context starvation)
   - Low risk: Pure computation on existing OHLCV data

2. **Phase 2: Support/Resistance Engine** — Pivot points, Fibonacci retracements, swing high/low detection
   - Addresses: Price level context for entry/SL/TP generation
   - Avoids: Premature Gemini integration without price structure context
   - Low risk: Pure math, no external dependencies

3. **Phase 3: Trading Signal Schema + Gemini Integration** — Pydantic schemas, new AnalysisType, prompt engineering, Gemini calls
   - Addresses: Core LONG/SHORT analysis + trading plan generation
   - Avoids: Building UI before the data pipeline works
   - Medium risk: Prompt engineering iteration needed for realistic price targets

4. **Phase 4: Dashboard Trading Plan Panel** — Frontend component for displaying trading plans on ticker detail page
   - Addresses: User-facing display of trading plans
   - Avoids: Building frontend without stable API contract
   - Low risk: Follows existing analysis-card.tsx pattern

5. **Phase 5: Price Line Overlays + Telegram Alerts** — lightweight-charts entry/SL/TP lines + Telegram trading plan messages
   - Addresses: Visual chart overlay + notification delivery
   - Avoids: Polish features before core works
   - Low risk: Additive features on working foundation

**Phase ordering rationale:**
- Phase 1 → 2: Indicators must exist before S/R engine can use them (ATR for stop-loss, ADX for direction confidence)
- Phase 2 → 3: Gemini needs full context (indicators + price levels) to generate realistic trading plans
- Phase 3 → 4: Frontend needs stable API response shape before building display components
- Phase 4 → 5: Chart overlay and Telegram are polish — core display must work first

**Research flags for phases:**
- Phase 3: Likely needs iterative prompt engineering research — testing few-shot examples for realistic VN market price targets
- Phase 5: lightweight-charts `createPriceLine` API needs verification against v5.1.0 docs (MEDIUM confidence from training data)
- Phase 1-2: Standard patterns, unlikely to need additional research

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All verified with actual code execution on installed packages |
| Features | HIGH | Clear scope from PROJECT.md, well-defined boundaries |
| Architecture | HIGH | Extends existing proven patterns (analysis types, batching, JSONB storage) |
| Pitfalls | MEDIUM | Token budget estimates are theoretical — actual Gemini output length varies. Price target realism depends on prompt quality. |

## Gaps to Address

- Gemini's actual output quality for dual-direction analysis needs testing — may need multiple prompt iterations to get both LONG and SHORT analyses to be meaningful (not just "confidence 1" for the non-recommended direction)
- VN market–specific trading constraints (T+2.5 settlement, floor/ceiling prices ±7%) should be encoded in prompts — needs research on how Gemini handles VN-specific constraints
- Optimal `thinking_budget` for trading signal complexity — 1024 (current) vs 2048 (proposed) needs A/B testing
- lightweight-charts v5.1.0 `createPriceLine` API specifics should be verified against official docs before Phase 5
