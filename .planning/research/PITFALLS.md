# Domain Pitfalls — v3.0 Smart Trading Signals

**Domain:** AI-powered dual-direction trading signal generation
**Researched:** 2026-04-20

## Critical Pitfalls

Mistakes that cause rewrites, bad user decisions, or broken pipeline.

### Pitfall 1: Gemini Generates Unrealistic Price Targets

**What goes wrong:** Gemini outputs entry/SL/TP prices that are physically impossible (SL below zero, TP above 52-week high by 50%, entry price nowhere near current price) or violate VN market constraints (±7% daily limit).

**Why it happens:** Without anchoring context, Gemini generates "reasonable-sounding" numbers that don't correspond to actual market structure. The model doesn't inherently know the current price or historical ranges.

**Consequences:** Users set orders at invalid prices. Credibility of the entire signal system destroyed. Could lead to real financial losses if users blindly trust prices.

**Prevention:**
1. **Always include current price, ATR, and price levels in prompt.** Gemini must see: current close, 14-day ATR, pivot points (S1/S2/R1/R2), Fibonacci levels, 52-week high/low, Bollinger bands. This gives anchoring context.
2. **Post-validation in Pydantic or backend.** After `response.parsed`, validate:
   - SL is within 3×ATR of entry
   - TP is within 5×ATR of entry
   - Entry is within 2% of current price (for swing) or 5% (for position)
   - All prices > 0
   - R:R ratio matches computed `abs(TP-entry)/abs(entry-SL)`
3. **Prompt engineering:** Include explicit constraints: "Entry price must be within ±5% of current price. Stop-loss must be within 2×ATR of entry."

**Detection:** Monitor `ai_analyses` where `analysis_type='trading_signal'` — extract entry/SL/TP from `raw_response` JSONB and flag entries where prices deviate >10% from current close.

### Pitfall 2: Meaningless SHORT Signals for VN Market

**What goes wrong:** The SHORT analysis is always "confidence 1, don't short" because VN market doesn't have accessible short-selling for retail investors. Users see two tabs (LONG/SHORT) where SHORT is always useless.

**Why it happens:** Dual-direction analysis assumes both directions are actionable. In VN equity markets, retail short-selling is extremely limited (SBL mechanism, few brokers, restricted tickers).

**Consequences:** UX feels padded — users learn to ignore SHORT analysis entirely, reducing trust in the system.

**Prevention:**
1. **Reframe SHORT as "bearish outlook"** in the prompt and UI. Not "short sell this stock" but "this stock has bearish signals — avoid buying / consider reducing position."
2. **System instruction explicitly states:** "SHORT analysis means bearish outlook and selling pressure, NOT literal short-selling. Recommend 'giảm vị thế' (reduce position) or 'tránh mua' (avoid buying) instead of 'bán khống' (short sell)."
3. **UI labels:** Use "Xu hướng GIẢM" (bearish trend) instead of "SHORT" — localized for VN context.
4. **Still generate concrete SHORT targets** — they're useful for stop-loss placement on existing LONG positions and for understanding downside risk.

**Detection:** If >90% of SHORT signals have confidence ≤2, the prompt needs adjustment to make SHORT analysis more nuanced.

### Pitfall 3: Token Budget Blowout from Verbose Trading Plans

**What goes wrong:** With 25 tickers per batch and dual-direction detailed plans per ticker, Gemini's output exceeds `max_output_tokens=16384`, causing truncated JSON that fails parsing.

**Why it happens:** Current analyses output ~60 tokens/ticker. Trading signals output ~300 tokens/ticker. At 25 tickers: 7,500 output tokens (within limit). But with verbose reasoning + thinking tokens, it can spike to 12,000-15,000+ output tokens, approaching the 16K limit.

**Consequences:** `response.parsed` returns `None`. The fallback manual JSON parse also fails on truncated JSON. Entire batch lost.

**Prevention:**
1. **Reduce batch size to 15 tickers** for trading signals specifically. At 300 tokens/ticker × 15 = 4,500 output tokens — comfortable margin.
2. **Constrain reasoning length in schema:** `reasoning: str = Field(max_length=300, description="Tối đa 100 từ tiếng Việt")`. Gemini generally respects length hints.
3. **Increase `max_output_tokens` to 32768** for trading signal calls (Gemini 2.5 flash lite supports up to 65K output).
4. **Monitor via GeminiUsage:** Track `completion_tokens` for `analysis_type='trading_signal'`. Alert if average exceeds 10,000.

**Detection:** `response.parsed is None` with non-empty `response.text` that ends without closing `}` — indicates truncation. Already handled by existing fallback pattern but should be monitored.

### Pitfall 4: Trading Signals Stale After Market Open

**What goes wrong:** Signals generated at 15:30 (after market close) show entry prices that gap past the target when market opens next morning due to overnight news or gap-up/gap-down.

**Why it happens:** VN market can gap significantly at open. A signal saying "Entry: 25,000 VND" is meaningless if the stock opens at 26,500 VND.

**Consequences:** Users attempt to enter at stale prices, get bad fills or miss the move entirely. Creates false sense of precision.

**Prevention:**
1. **Display clear timestamp:** "Tín hiệu phân tích ngày 20/04/2026 lúc 15:45" — prominently, not hidden.
2. **Entry as a ZONE, not a point:** Instead of `entry_price: 25000`, use `entry_zone_low: 24500, entry_zone_high: 25500`. Gemini can generate zones based on ATR.
3. **Prompt instruction:** "Entry price is for reference. Real entries should be at market price within the entry zone."
4. **Frontend disclaimer:** "Giá vào lệnh mang tính tham khảo. Cần kiểm tra giá thực tế tại thời điểm giao dịch."

**Detection:** Not detectable automatically. Mitigated by UX design.

## Moderate Pitfalls

### Pitfall 5: R:R Ratio Gaming by Gemini

**What goes wrong:** Gemini learns that high R:R ratios look good and generates artificially favorable R:R by setting very wide TP and very tight SL — e.g., SL at -1% with TP at +15% = R:R of 15.0, but the SL is so tight it would trigger immediately on normal volatility.

**Prevention:**
1. Validate R:R in context of ATR: `SL distance should be >= 1.0 × ATR(14)`. If SL is tighter than 1 ATR, flag as unrealistic.
2. Cap R:R display at reasonable range (e.g., 0.5 to 5.0). Anything outside = Gemini hallucinating.
3. Prompt: "Stop-loss should be at least 1× ATR(14) from entry price to avoid premature triggering."

### Pitfall 6: Indicator Warm-Up Period for New Tickers

**What goes wrong:** New tickers (recently IPO'd or recently added to UPCOM) have <14 days of data. ATR(14) and ADX(14) return NaN. Trading signal context is incomplete, leading to low-quality signals.

**Prevention:**
1. Skip trading signal generation for tickers with <30 days of price data (same pattern as existing indicator skip at <20 rows).
2. In prompt, explicitly state when indicators are unavailable: "ATR: N/A (insufficient data)" — Gemini generates wider entry zones when volatility data is missing.

### Pitfall 7: PostgreSQL ENUM Migration Is One-Way

**What goes wrong:** `ALTER TYPE analysis_type ADD VALUE 'trading_signal'` is not reversible in PostgreSQL. If you need to rename or remove the value, you can't use a simple migration rollback.

**Prevention:**
1. Verify the enum value name is final before migrating. `trading_signal` is descriptive and consistent with existing pattern.
2. Alembic downgrade should NOT attempt to remove the enum value — just document that it's a one-way migration.
3. Test migration on development DB first.

### Pitfall 8: Frontend Schema Coupling

**What goes wrong:** Frontend `AnalysisSummary` TypeScript interface doesn't include `trading_signal` field. Or the `raw_response` JSONB shape changes in backend but frontend still renders old shape.

**Prevention:**
1. Extend `AnalysisSummary` interface: `trading_signal?: AnalysisResult;`
2. Parse `raw_response` with a dedicated TypeScript type `TradingSignalDetail` (matching the Pydantic schema).
3. Defensive rendering: check for `trading_signal?.raw_response?.long_analysis?.trading_plan` before accessing nested fields. Use optional chaining throughout.

## Minor Pitfalls

### Pitfall 9: Gemini Inconsistent Ticker Names in Response

**What goes wrong:** Gemini returns `"ticker": "vnm"` (lowercase) instead of `"ticker": "VNM"` (uppercase as sent), causing the symbol lookup `ticker_ids.get(symbol)` to miss.

**Prevention:** Already handled in existing code — but verify the trading signal parsing normalizes ticker to uppercase: `symbol = analysis.ticker.upper()`.

### Pitfall 10: ThinkingConfig Budget Too Low for Complex Reasoning

**What goes wrong:** With `thinking_budget=1024`, Gemini's internal reasoning gets truncated before it fully analyzes both directions, leading to copy-paste-like SHORT analysis that mirrors LONG with flipped direction.

**Prevention:** Set `thinking_budget=2048` for trading signal calls. Monitor output quality — if SHORT analyses lack specificity, increase further.

### Pitfall 11: Stochastic + RSI Redundancy in Prompt

**What goes wrong:** Both RSI and Stochastic measure overbought/oversold. Including both in the prompt without context wastes tokens and can confuse Gemini when they give contradictory signals.

**Prevention:** In prompt, explain the relationship: "RSI measures momentum, Stochastic measures closing price relative to range. When both agree on overbought/oversold, signal is stronger."

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|-------------|---------------|------------|
| Enhanced indicators (Phase 1) | ATR/ADX/Stochastic need OHLCV, not just close. `indicator_service` currently queries only `DailyPrice.close`. | Extend query to include `high`, `low`, `volume` columns. |
| Support/resistance (Phase 2) | Swing high/low detection on noisy daily data produces too many levels | Use minimum swing size = 2×ATR to filter noise. Limit to 3 nearest levels above/below current price. |
| Gemini integration (Phase 3) | First prompt iteration produces generic/unrealistic plans | Budget 2-3 prompt iterations. Test with 5 well-known tickers (VNM, HPG, FPT, VCB, MBB) before batch rollout. |
| Dashboard panel (Phase 4) | Trading plan detail overwhelms the ticker detail page — too much information | Use collapsible/tabbed UI. Show recommended direction prominently, hide non-recommended direction behind tab. |
| Price line overlay (Phase 5) | Too many lines on chart (entry + SL + TP1 + TP2 × 2 directions = 10 lines) | Only show recommended direction's lines. Toggle for showing other direction. |
| Telegram alerts (Phase 5) | Trading plan message too long for Telegram (4096 char limit) | Show only recommended direction in alert. Link to dashboard for full plan. |

## Sources

- `backend/app/services/ai_analysis_service.py` — Existing error handling, fallback parsing, batch failure patterns
- `backend/app/services/indicator_service.py` — Warm-up period handling (skip <20 rows)
- `backend/app/models/ai_analysis.py` — JSONB storage pattern, PostgreSQL ENUM
- `frontend/src/components/analysis-card.tsx` — Signal display pattern, defensive rendering
- VN market constraints (T+2.5, ±7%, no retail short-selling) — training data, MEDIUM confidence
- Gemini structured output behavior with large schemas — verified with code execution
