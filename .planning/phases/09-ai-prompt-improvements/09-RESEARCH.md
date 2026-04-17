# Phase 9: AI Prompt Improvements - Research

**Researched:** 2026-04-18
**Domain:** Google Gemini prompt engineering, structured output, google-genai SDK
**Confidence:** HIGH

## Summary

Phase 9 targets 7 improvements to the `AIAnalysisService` in `backend/app/services/ai_analysis_service.py` — the single file containing all AI prompt construction, Gemini API calls, context gathering, and result storage. The current implementation uses inline prompt strings with persona baked into user content, a hardcoded temperature of 0.2 for all analysis types, and a simple JSON parse fallback for structured output failures. No `system_instruction` or few-shot examples are used.

The google-genai SDK v1.73.1 (installed) supports `system_instruction` as a field on `GenerateContentConfig`, which gets hoisted to the top-level `systemInstruction` in the API request body. This is the correct place for persona/role definition and scoring rubrics. The refactoring scope is moderate — ~12 methods need changes within a single service file, plus new constants for system instructions, few-shot examples, and per-type temperature configuration. One new DB query is needed (latest close price from `daily_prices`).

**Primary recommendation:** Refactor in 3 waves — (1) system instructions + rubric + temperature per type, (2) few-shot examples + language consistency + technical prompt data enhancement, (3) structured output retry at low temperature.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- D-09-01: Move persona definition to `system_instruction` parameter in Gemini API call. User prompt contains only data + specific analysis request.
- D-09-02: Add 1-2 few-shot examples per analysis type showing expected input → output format. Store examples as constants in the service module.
- D-09-03: Define explicit scoring rubric: 1-2 (very weak/negative), 3-4 (weak/slightly negative), 5-6 (moderate/neutral), 7-8 (strong/positive), 9-10 (very strong/very positive). Include in system instruction.
- D-09-04: Add latest close price and price-vs-SMA percentage distances to technical analysis input data.
- D-09-05: Language consistency — Technical: English, Fundamental: English, Sentiment: Vietnamese, Combined: Vietnamese.
- D-09-06: Temperature tuning — Technical=0.1, Fundamental=0.2, Sentiment=0.3, Combined=0.2.
- D-09-07: On structured output failure (Gemini returns malformed JSON), retry once at temperature=0.05 before falling back to manual JSON parsing.

### Copilot's Discretion
- Whether to create a separate `prompts/` module or keep prompts in the service with `_build_system_instruction()` methods
- Few-shot examples should use realistic VN stock data (VNM, HPG, etc.)

### Deferred Ideas (OUT OF SCOPE)
- None — all AI-07 through AI-13 requirements are in scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| AI-07 | AI prompts use `system_instruction` for persona separation | SDK confirmed: `system_instruction` on `GenerateContentConfig` (line 5812 of types.py); SDK example at line 8294 of models.py |
| AI-08 | AI prompts include few-shot examples per analysis type | Few-shot goes in user prompt content as example input→output pairs; system_instruction for persona/rubric |
| AI-09 | Scoring rubric with explicit anchors (1-2 through 9-10) | Include in system_instruction alongside persona definition |
| AI-10 | Technical prompt includes latest close price and price-vs-SMA percentages | Need new query to `daily_prices` table for latest `close`; compute `(close - sma) / sma * 100` |
| AI-11 | Language consistency per analysis type | Currently mostly correct; formalize in system_instruction language |
| AI-12 | Structured output failures trigger low-temp retry before JSON parse | Modify `_analyze_*_batch` methods to retry at temp=0.05 before existing JSON parse fallback |
| AI-13 | Temperature tuned per analysis type | Replace hardcoded 0.2 in `_call_gemini_with_retry`; pass per-type temperature |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| google-genai | 1.73.1 | Gemini API client (new unified SDK) | Already installed; `system_instruction` on `GenerateContentConfig` confirmed | [VERIFIED: pip show + SDK source inspection] |
| pydantic | (bundled) | Response schemas for structured output | Already used for all 4 `*BatchResponse` schemas | [VERIFIED: codebase] |
| tenacity | (bundled) | Retry with exponential backoff | Already used by `_call_gemini_with_retry` | [VERIFIED: codebase] |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| sqlalchemy | (bundled) | DB queries for close price | Already used throughout; need one new query for `DailyPrice.close` | [VERIFIED: codebase] |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Constants in service file | Separate `prompts/` module | Separate module is cleaner for large prompt text but adds file management overhead for 4 analysis types. **Recommend: keep in service file** — prompts are tightly coupled to the data format each method produces |

## Architecture Patterns

### Current Architecture (Single File)
```
backend/app/services/ai_analysis_service.py  (890 lines, ~37.8 KB)
├── AIAnalysisService class
│   ├── Public API: analyze_all_tickers, run_*_analysis (4 types)
│   ├── Batching: _run_batched_analysis
│   ├── Gemini calls: _call_gemini_with_retry, _call_gemini
│   ├── Batch analyzers: _analyze_*_batch (4 types)
│   ├── Context gatherers: _get_*_context (4 types)
│   ├── Prompt builders: _build_*_prompt (4 types)
│   └── Storage: _store_analysis
```

### Recommended Modification Pattern

```
backend/app/services/ai_analysis_service.py
├── MODULE-LEVEL CONSTANTS (new)
│   ├── TECHNICAL_SYSTEM_INSTRUCTION
│   ├── FUNDAMENTAL_SYSTEM_INSTRUCTION
│   ├── SENTIMENT_SYSTEM_INSTRUCTION
│   ├── COMBINED_SYSTEM_INSTRUCTION
│   ├── SCORING_RUBRIC (shared text block)
│   ├── TECHNICAL_FEW_SHOT_EXAMPLES
│   ├── FUNDAMENTAL_FEW_SHOT_EXAMPLES
│   ├── SENTIMENT_FEW_SHOT_EXAMPLES
│   ├── COMBINED_FEW_SHOT_EXAMPLES
│   └── ANALYSIS_TEMPERATURES: dict[AnalysisType, float]
├── AIAnalysisService class (modified methods)
│   ├── _call_gemini_with_retry(prompt, response_schema, temperature, system_instruction)  # MODIFIED
│   ├── _call_gemini(prompt, response_schema, temperature, system_instruction)  # MODIFIED
│   ├── _analyze_*_batch  # MODIFIED: pass temperature + system_instruction, add low-temp retry
│   ├── _get_technical_context  # MODIFIED: add close price + SMA distances
│   ├── _build_technical_prompt  # MODIFIED: remove persona, add few-shot, add close/SMA data
│   ├── _build_fundamental_prompt  # MODIFIED: remove persona, add few-shot
│   ├── _build_sentiment_prompt  # MODIFIED: remove persona, add few-shot
│   └── _build_combined_prompt  # MODIFIED: remove persona, add few-shot
```

### Pattern 1: System Instruction via GenerateContentConfig
**What:** Pass persona and rubric as `system_instruction` parameter on `GenerateContentConfig`
**When to use:** Every Gemini API call
**Example:**
```python
# Source: [VERIFIED: google-genai SDK v1.73.1 source, models.py line 8294-8303]
response = await self.client.aio.models.generate_content(
    model=self.model,
    contents=prompt,  # data + analysis request only
    config=types.GenerateContentConfig(
        system_instruction=TECHNICAL_SYSTEM_INSTRUCTION,  # persona + rubric
        response_mime_type="application/json",
        response_schema=response_schema,
        temperature=0.1,
        max_output_tokens=16384,
        thinking_config=thinking_config,
    ),
)
```

### Pattern 2: Per-Type Temperature with Low-Temp Retry
**What:** Pass analysis-specific temperature, retry at 0.05 on structured output failure
**When to use:** All `_analyze_*_batch` methods
**Example:**
```python
# In _analyze_technical_batch:
async def _analyze_technical_batch(self, ticker_data):
    prompt = self._build_technical_prompt(ticker_data)
    system_instr = TECHNICAL_SYSTEM_INSTRUCTION
    temp = ANALYSIS_TEMPERATURES[AnalysisType.TECHNICAL]  # 0.1

    response = await self._call_gemini(prompt, TechnicalBatchResponse, temp, system_instr)
    result = response.parsed

    if result is None and response.text:
        # Low-temperature retry (D-09-07)
        logger.warning("response.parsed is None, retrying at temperature=0.05")
        response = await self._call_gemini(prompt, TechnicalBatchResponse, 0.05, system_instr)
        result = response.parsed

    if result is None and response.text:
        # Final fallback: manual JSON parse
        logger.warning("Low-temp retry also failed, falling back to manual JSON parse")
        try:
            data = json.loads(response.text)
            result = TechnicalBatchResponse.model_validate(data)
        except Exception as e:
            logger.error(f"Manual parse also failed: {e}")

    return result
```

### Pattern 3: Few-Shot in User Prompt
**What:** Include example input→output pairs in the user prompt content (not system_instruction)
**When to use:** All prompt builder methods
**Example:**
```python
TECHNICAL_FEW_SHOT = """
Example analysis:
--- VNM ---
RSI(14) last 5 days: [42.1, 43.5, 45.2, 47.8, 52.3]
RSI zone: neutral
MACD crossover: bullish
Latest close: 78,500 VND
Price vs SMA(20): +2.3%, Price vs SMA(50): -1.5%, Price vs SMA(200): +8.7%

Expected output for VNM:
{"ticker": "VNM", "signal": "buy", "strength": 7, "reasoning": "RSI rising from mid-range with bullish MACD crossover. Price above SMA20 and SMA200 but slightly below SMA50, suggesting short-term momentum building within a longer uptrend."}
"""
```

### Anti-Patterns to Avoid
- **Persona in user prompt:** Persona ("You are a...") goes in system_instruction, NOT in user content. Mixing them causes Gemini to sometimes ignore or partially follow the persona. [ASSUMED — based on Gemini prompt engineering best practices]
- **Few-shot in system_instruction:** System instruction is for stable behavior rules. Few-shot examples with varying data belong in user content to avoid inflating system instruction size. [ASSUMED — standard practice]
- **Same temperature for all types:** Quantitative analysis (technical) needs lower temp for determinism; language tasks (sentiment) benefit from slightly higher temp for nuance. [ASSUMED — general LLM practice]
- **Retry at same temperature:** If structured output fails, retrying at the same temperature often produces the same failure. Dropping to near-zero temperature increases structured compliance. [ASSUMED — LLM behavior pattern]

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| System instruction passing | Custom header injection | `GenerateContentConfig(system_instruction=...)` | SDK handles serialization to API format | [VERIFIED: SDK source] |
| Structured output validation | Custom JSON schema checking | Pydantic `response_schema` + `response.parsed` | Already works; SDK validates against schema | [VERIFIED: codebase] |
| Retry logic | Custom retry wrapper | tenacity `@retry` decorator (already used) | Handles backoff, attempt counting | [VERIFIED: codebase] |
| Price-vs-SMA calculation | Complex indicator library | Simple `(close - sma) / sma * 100` arithmetic | Three lines of code, no library needed | [VERIFIED: straightforward math] |

## Current Code Audit

### Current Prompt Texts (Verbatim)

**Technical (English):**
```
You are a Vietnamese stock market (HOSE) technical analyst. Analyze the following tickers based on their technical indicators from the last 5 trading days.

For each ticker, provide:
- signal: one of strong_buy, buy, neutral, sell, strong_sell
- strength: 1-10 (confidence in the signal)
- reasoning: brief explanation (2-3 sentences in English)

Consider RSI zones (oversold <30 = bullish, overbought >70 = bearish), MACD crossovers, price position relative to moving averages, and Bollinger Band positions.

Tickers:
--- {SYMBOL} ---
RSI(14) last 5 days: [...]
RSI zone: ...
MACD line/signal/histogram last 5 days: [...]
MACD crossover: ...
SMA(20): ..., SMA(50): ..., SMA(200): ...
EMA(12): ..., EMA(26): ...
Bollinger Bands — Upper: ..., Middle: ..., Lower: ...
```
[VERIFIED: lines 725-756 of ai_analysis_service.py]

**Fundamental (English):**
```
You are a Vietnamese stock market (HOSE) fundamental analyst. Evaluate the financial health of the following tickers based on their most recent financial data.

For each ticker, provide:
- health: one of strong, good, neutral, weak, critical
- score: 1-10 (overall financial health score)
- reasoning: brief explanation (2-3 sentences in English)

Consider P/E relative to sector averages (Vietnam market P/E ~12-15), profitability (ROE, ROA), growth rates, and financial stability (current ratio, debt-to-equity).

Tickers:
--- {SYMBOL} (Period: ...) ---
P/E: ..., P/B: ..., EPS: ...
ROE: ..., ROA: ...
Revenue Growth: ..., Profit Growth: ...
Current Ratio: ..., Debt/Equity: ...
```
[VERIFIED: lines 758-784]

**Sentiment (Vietnamese):**
```
Bạn là chuyên gia phân tích tâm lý thị trường chứng khoán Việt Nam (HOSE). Phân tích tiêu đề tin tức gần đây cho các mã cổ phiếu sau.

Cho mỗi mã, đánh giá:
- sentiment: very_positive, positive, neutral, negative, very_negative
- score: 1-10 (1 = rất tiêu cực, 10 = rất tích cực)
- reasoning: giải thích ngắn gọn bằng tiếng Việt (2-3 câu)

Lưu ý: Nếu không có tin tức, sentiment = neutral, score = 5.

Các mã cổ phiếu:
--- {SYMBOL} ({N} tin tức) ---
1. {title}
2. {title}
```
[VERIFIED: lines 786-815]

**Combined (Vietnamese):**
```
Bạn là chuyên gia tư vấn đầu tư chứng khoán Việt Nam (HOSE). Dựa trên 3 chiều phân tích (kỹ thuật, cơ bản, tâm lý thị trường), đưa ra khuyến nghị tổng hợp cho các mã sau.

Cho mỗi mã, cung cấp:
- recommendation: mua, ban, giu
- confidence: 1-10 (dựa trên sự đồng thuận giữa 3 chiều, độ tươi dữ liệu, lượng tin)
- explanation: giải thích bằng tiếng Việt, tối đa 200 từ, ngôn ngữ tự nhiên

Quy tắc confidence:
- 8-10: Cả 3 chiều đồng thuận, dữ liệu đầy đủ và mới
- 5-7: 2/3 chiều đồng thuận, hoặc dữ liệu không đầy đủ
- 1-4: Tín hiệu mâu thuẫn, hoặc thiếu dữ liệu nghiêm trọng

Các mã cổ phiếu:
--- {SYMBOL} ---
Kỹ thuật: signal=..., strength=...
Cơ bản: health=..., score=...
Tâm lý: sentiment=..., score=...
```
[VERIFIED: lines 817-849]

### Current Temperature Configuration
- **All analysis types:** hardcoded `temperature=0.2` in `_call_gemini_with_retry` (line 428)
- No per-type differentiation exists
[VERIFIED: line 428 of ai_analysis_service.py]

### Current Retry/Fallback Behavior
1. `_call_gemini_with_retry`: tenacity retries **2 attempts** on `ServerError` with exponential backoff (2x, min=4s, max=15s)
2. `_call_gemini`: wraps with `gemini_breaker.call()` (circuit breaker: 3 failures → open, 120s reset)
3. Batch-level: 5 retries for 429 rate limits (parses retry delay from error) and ServerError (progressive wait: 30s, 60s, 90s...)
4. Each `_analyze_*_batch`: if `response.parsed is None` and `response.text` exists → `json.loads()` → Pydantic `model_validate()`
5. **No low-temperature retry exists** — goes directly from `response.parsed is None` to JSON parse fallback
[VERIFIED: lines 408-520]

### Technical Context Data (What's Included vs Missing)
**Currently included:**
- RSI(14) — 5-day array + zone classification
- MACD line/signal/histogram — 5-day arrays + crossover detection
- SMA(20), SMA(50), SMA(200) — latest values only
- EMA(12), EMA(26) — latest values only
- Bollinger Bands — upper/middle/lower

**Currently MISSING (needed for AI-10):**
- Latest close price (from `daily_prices` table)
- Price vs SMA(20) percentage distance
- Price vs SMA(50) percentage distance
- Price vs SMA(200) percentage distance
[VERIFIED: lines 526-593 — `_get_technical_context` queries only `TechnicalIndicator`, not `DailyPrice`]

### Structured Output Schemas
All 4 schemas are clean Pydantic models already working with `response_schema`:
- `TechnicalBatchResponse` → `analyses: list[TickerTechnicalAnalysis]`
- `FundamentalBatchResponse` → `analyses: list[TickerFundamentalAnalysis]`
- `SentimentBatchResponse` → `analyses: list[TickerSentimentAnalysis]`
- `CombinedBatchResponse` → `analyses: list[TickerCombinedAnalysis]`
No schema changes needed. [VERIFIED: schemas/analysis.py]

## Impact Assessment: Methods Requiring Modification

| Method | Change Type | Requirement | Complexity |
|--------|-------------|-------------|------------|
| `_call_gemini_with_retry` | Add `temperature` + `system_instruction` params | AI-07, AI-13 | Low |
| `_call_gemini` | Pass through new params | AI-07, AI-13 | Low |
| `_analyze_technical_batch` | Add system_instruction, temperature, low-temp retry | AI-07, AI-12, AI-13 | Medium |
| `_analyze_fundamental_batch` | Same | AI-07, AI-12, AI-13 | Medium |
| `_analyze_sentiment_batch` | Same | AI-07, AI-12, AI-13 | Medium |
| `_analyze_combined_batch` | Same | AI-07, AI-12, AI-13 | Medium |
| `_build_technical_prompt` | Remove persona, add few-shot, add close/SMA data | AI-08, AI-10, AI-11 | Medium |
| `_build_fundamental_prompt` | Remove persona, add few-shot | AI-08, AI-11 | Low |
| `_build_sentiment_prompt` | Remove persona, add few-shot | AI-08, AI-11 | Low |
| `_build_combined_prompt` | Remove persona, add few-shot | AI-08, AI-11 | Low |
| `_get_technical_context` | Add DailyPrice query + SMA distances | AI-10 | Medium |
| **New constants** | System instructions, few-shot, rubric, temperatures | AI-07-09 | Medium |

**Total: 11 existing methods modified + new module-level constants. Single file scope.**

## SDK Findings: system_instruction

### How It Works
`system_instruction` is a field on `types.GenerateContentConfig` (line 5812 of types.py). The SDK's mldev transformer (line 1184-1193 of models.py) hoists it from config to the parent request object as `systemInstruction`, which is the correct API-level placement. [VERIFIED: SDK source code inspection]

### Usage Example (from SDK source)
```python
# Source: [VERIFIED: google-genai SDK v1.73.1, models.py lines 8294-8303]
response = await client.aio.models.generate_content(
    model='gemini-2.0-flash',
    contents='User input: I like bagels. Answer:',
    config=types.GenerateContentConfig(
        system_instruction=[
            'You are a helpful language translator.',
            'Your mission is to translate text in English to French.'
        ]
    ),
)
```

### Type Accepted
`system_instruction: Optional[ContentUnion]` — accepts string, list of strings, or `Content` objects. A plain string is the simplest and correct approach for our persona + rubric text. [VERIFIED: types.py line 5812]

### Compatibility with response_schema
`system_instruction` and `response_schema` can coexist on the same `GenerateContentConfig` — they are independent fields. The SDK handles both in the same request. [VERIFIED: both fields present in `GenerateContentConfig` class definition, no mutual exclusion logic]

## Few-Shot Example Placement

### Where to Put Them
Few-shot examples should go in the **user prompt content**, not in `system_instruction`. Reasons:
1. System instruction is for persistent behavior rules (persona, rubric, language). It should be concise and stable.
2. Few-shot examples include variable data formats that mirror the actual analysis data — they belong alongside the data.
3. The Gemini API processes system_instruction as a separate context frame. Large system instructions can reduce context window for actual content.
[ASSUMED — standard Gemini prompt engineering practice; confirmed that system_instruction is Content type supporting arbitrary text]

### Recommended Structure Per Prompt
```
system_instruction: persona + scoring rubric + language rule + output format rules
user prompt: few-shot example(s) + "Now analyze:" + actual ticker data
```

## Close Price Query for AI-10

### Data Source
`DailyPrice` model (`backend/app/models/daily_price.py`) has `close: Decimal(12,2)`. Need to query the latest close price per ticker within `_get_technical_context`. [VERIFIED: daily_price.py line 28]

### Implementation Approach
```python
# Add to _get_technical_context after existing indicator query:
from app.models.daily_price import DailyPrice

price_result = await self.session.execute(
    select(DailyPrice.close)
    .where(DailyPrice.ticker_id == ticker_id)
    .order_by(DailyPrice.date.desc())
    .limit(1)
)
latest_close = price_result.scalar_one_or_none()

if latest_close is not None:
    close_float = float(latest_close)
    context["latest_close"] = close_float
    # Compute price vs SMA distances
    for sma_key in ["sma_20", "sma_50", "sma_200"]:
        sma_val = context.get(sma_key)
        if sma_val is not None and sma_val != 0:
            pct = (close_float - sma_val) / sma_val * 100
            context[f"price_vs_{sma_key}_pct"] = round(pct, 2)
```

## Common Pitfalls

### Pitfall 1: System Instruction + Thinking Config Interaction
**What goes wrong:** With thinking models (gemini-2.5-*), very long system instructions can consume thinking budget, reducing quality of the actual analysis.
**Why it happens:** Thinking budget (currently 1024 tokens) is shared across all model reasoning including understanding system instructions.
**How to avoid:** Keep system instructions concise — persona (1-2 sentences), rubric (5 lines), language rule (1 line). Don't put few-shot examples in system_instruction.
**Warning signs:** Shorter/lower-quality reasoning in output after adding long system instructions.
[ASSUMED — based on thinking model behavior patterns]

### Pitfall 2: Low-Temperature Retry Doubles API Cost
**What goes wrong:** Every structured output failure triggers an additional API call, potentially doubling cost/time for problematic batches.
**Why it happens:** The retry at temperature=0.05 is a full new API call, not a parse retry.
**How to avoid:** Only retry once (as specified in D-09-07). Log the retry so it's visible in monitoring. Keep the manual JSON parse as final fallback — it's free.
**Warning signs:** High frequency of "retrying at temperature=0.05" log messages.
[VERIFIED: current code already limits to 1 JSON parse fallback per batch]

### Pitfall 3: Few-Shot Examples Inflating Prompt Token Count
**What goes wrong:** With 25 tickers per batch + 1-2 few-shot examples, total token count could approach limits.
**Why it happens:** Each few-shot example adds ~100-200 tokens. With 25 tickers × ~15 lines each = ~375 lines of data, examples add ~10-15% more.
**How to avoid:** Keep examples minimal (1 example per type, 1 ticker per example). Max_output_tokens is 16384 which is generous. Monitor `response.usage_metadata.total_token_count` (already logged).
**Warning signs:** Token count approaching model limits; truncated responses.
[VERIFIED: batch_size=25 per settings; token logging already exists in each _analyze_*_batch method]

### Pitfall 4: Breaking Existing Tests
**What goes wrong:** Prompt builder tests assert specific strings that change after refactoring.
**Why it happens:** Tests like `test_technical_prompt_includes_ticker_symbols` check that "VNM" and "FPT" appear in the prompt. These will still pass. But assertions on specific content (like `"Không có tin tức"`) may need updates if prompt text changes.
**How to avoid:** Review all 7 existing test methods in `test_ai_analysis_service.py`. Most check for ticker symbols and general content, not exact text — they should survive refactoring. Update any that break.
**Warning signs:** Test failures on exact string matches.
[VERIFIED: tests/test_ai_analysis_service.py has 7 tests across 5 classes]

### Pitfall 5: Tenacity Decorator + New Parameters
**What goes wrong:** Adding `temperature` and `system_instruction` parameters to `_call_gemini_with_retry` — the `@retry` decorator must not interfere with the new parameters.
**Why it happens:** tenacity wraps the function; additional keyword args pass through fine as long as the function signature accepts them.
**How to avoid:** Just add the parameters to the function signature. Tenacity's `@retry` is transparent to additional parameters.
**Warning signs:** TypeError on unexpected keyword arguments.
[VERIFIED: tenacity wraps via functools; additional args pass through]

## Code Examples

### System Instruction Constant (Technical Analysis)
```python
# Source: [VERIFIED: SDK supports plain string for system_instruction]
SCORING_RUBRIC = """
Scoring rubric (apply consistently):
- 1-2: Very weak signal / very negative outlook
- 3-4: Weak signal / slightly negative outlook
- 5-6: Moderate / neutral — no clear direction
- 7-8: Strong signal / positive outlook
- 9-10: Very strong signal / very positive outlook
Use the FULL range. Scores of 1-2 and 9-10 are valid for extreme cases.
"""

TECHNICAL_SYSTEM_INSTRUCTION = (
    "You are a senior Vietnamese stock market (HOSE) technical analyst. "
    "You analyze price action and technical indicators to generate trading signals. "
    "Your analysis must be data-driven and precise.\n\n"
    + SCORING_RUBRIC +
    "\nProvide reasoning in English. Be specific about which indicators drive your signal."
)
```

### Modified _call_gemini_with_retry
```python
@retry(
    stop=stop_after_attempt(2),
    wait=wait_exponential(multiplier=2, min=4, max=15),
    retry=retry_if_exception_type(ServerError),
    reraise=True,
)
async def _call_gemini_with_retry(
    self,
    prompt: str,
    response_schema,
    temperature: float = 0.2,
    system_instruction: str | None = None,
):
    """Internal: Gemini call with tenacity retry. Circuit breaker wraps this."""
    thinking_config = None
    if "2.5" in self.model:
        thinking_config = types.ThinkingConfig(thinking_budget=1024)

    response = await self.client.aio.models.generate_content(
        model=self.model,
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction=system_instruction,
            response_mime_type="application/json",
            response_schema=response_schema,
            temperature=temperature,
            max_output_tokens=16384,
            thinking_config=thinking_config,
        ),
    )
    return response
```

### Technical Context with Close Price (AI-10)
```python
# Add after existing indicator query in _get_technical_context:
from app.models.daily_price import DailyPrice

# Fetch latest close price
price_result = await self.session.execute(
    select(DailyPrice.close)
    .where(DailyPrice.ticker_id == ticker_id)
    .order_by(DailyPrice.date.desc())
    .limit(1)
)
latest_close_decimal = price_result.scalar_one_or_none()

if latest_close_decimal is not None:
    close_val = float(latest_close_decimal)
    context["latest_close"] = close_val
    for sma_key in ("sma_20", "sma_50", "sma_200"):
        sma_val = context.get(sma_key)
        if sma_val is not None and sma_val != 0:
            context[f"price_vs_{sma_key}_pct"] = round(
                (close_val - sma_val) / sma_val * 100, 2
            )
```

### Low-Temperature Retry Pattern (AI-12)
```python
async def _analyze_technical_batch(self, ticker_data):
    prompt = self._build_technical_prompt(ticker_data)
    temp = ANALYSIS_TEMPERATURES[AnalysisType.TECHNICAL]
    sys_instr = TECHNICAL_SYSTEM_INSTRUCTION

    response = await self._call_gemini(prompt, TechnicalBatchResponse, temp, sys_instr)
    result = response.parsed

    if result is None:
        # Phase 1: Low-temperature retry (AI-12)
        if response.text:
            logger.warning("response.parsed is None, retrying at temperature=0.05")
            response = await self._call_gemini(
                prompt, TechnicalBatchResponse, 0.05, sys_instr
            )
            result = response.parsed

        # Phase 2: Manual JSON parse fallback (existing)
        if result is None and response.text:
            logger.warning("Low-temp retry failed, falling back to manual JSON parse")
            try:
                data = json.loads(response.text)
                result = TechnicalBatchResponse.model_validate(data)
            except Exception as e:
                logger.error(f"Manual parse also failed: {e}")
                logger.debug(f"Raw response text: {response.text[:500]}")

    return result
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Persona in user prompt | `system_instruction` on config | google-genai SDK 1.x+ | Cleaner separation, better model adherence |
| Flat temperature for all | Per-task temperature tuning | General practice | Better calibration per domain |
| No rubric | Explicit scoring anchors | Prompt engineering best practice | Reduces score clustering around 5-7 |

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Few-shot examples belong in user prompt, not system_instruction | Few-Shot Placement | Low — either location works; user prompt is standard practice |
| A2 | Long system instructions may consume thinking budget in 2.5-flash-lite | Pitfall 1 | Low — current thinking budget (1024) is conservative; our system instructions will be short |
| A3 | Lower temperature retry improves structured output compliance | Pattern 2 / Pitfall 2 | Low — well-established LLM behavior; worst case retry fails and we fall back to JSON parse anyway |
| A4 | Scores cluster around 5-7 without explicit rubric anchors | D-09-03 rationale | Low — this is the main motivation for AI-09; if not happening, rubric is still beneficial |

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.4.2 + pytest-asyncio |
| Config file | `backend/pytest.ini` |
| Quick run command | `cd backend && python -m pytest tests/test_ai_analysis_service.py -x -q` |
| Full suite command | `cd backend && python -m pytest tests/ -x -q` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| AI-07 | system_instruction passed to GenerateContentConfig | unit | `pytest tests/test_ai_analysis_service.py::TestSystemInstruction -x` | ❌ Wave 0 |
| AI-08 | Few-shot examples present in prompt text | unit | `pytest tests/test_ai_analysis_service.py::TestPromptBuilding -x` | ✅ (needs update) |
| AI-09 | Scoring rubric text in system instruction | unit | `pytest tests/test_ai_analysis_service.py::TestSystemInstruction -x` | ❌ Wave 0 |
| AI-10 | Technical prompt includes close price + SMA distances | unit | `pytest tests/test_ai_analysis_service.py::TestPromptBuilding::test_technical_prompt_includes_close_price -x` | ❌ Wave 0 |
| AI-11 | Language matches per analysis type | unit | `pytest tests/test_ai_analysis_service.py::TestLanguageConsistency -x` | ❌ Wave 0 |
| AI-12 | Low-temp retry before JSON parse fallback | unit | `pytest tests/test_ai_analysis_service.py::TestStructuredOutputRetry -x` | ❌ Wave 0 |
| AI-13 | Per-type temperature passed to Gemini | unit | `pytest tests/test_ai_analysis_service.py::TestTemperatureConfig -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `cd backend && python -m pytest tests/test_ai_analysis_service.py -x -q`
- **Per wave merge:** `cd backend && python -m pytest tests/ -x -q`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `tests/test_ai_analysis_service.py::TestSystemInstruction` — covers AI-07, AI-09 (system_instruction passed, rubric present)
- [ ] `tests/test_ai_analysis_service.py::TestTemperatureConfig` — covers AI-13 (per-type temperature values)
- [ ] `tests/test_ai_analysis_service.py::TestStructuredOutputRetry` — covers AI-12 (low-temp retry before JSON parse)
- [ ] `tests/test_ai_analysis_service.py::TestLanguageConsistency` — covers AI-11 (English/Vietnamese per type)
- [ ] Update existing `TestPromptBuilding` tests — covers AI-08, AI-10 (few-shot, close price)

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | N/A — internal service, no user auth changes |
| V3 Session Management | no | N/A |
| V4 Access Control | no | N/A — no permission model changes |
| V5 Input Validation | yes | Pydantic schemas already validate all Gemini responses; no new user input |
| V6 Cryptography | no | N/A — API key handling unchanged |

### Known Threat Patterns

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Prompt injection via news titles | Tampering | News titles are read from DB (already scraped/stored); system_instruction separation provides additional defense | [ASSUMED — system_instruction separation is a defense-in-depth measure] |
| API key exposure in logs | Information Disclosure | Already handled — API key passed via env var, not logged | [VERIFIED: config.py] |

## Sources

### Primary (HIGH confidence)
- google-genai SDK v1.73.1 source code (installed at `backend/.venv/Lib/site-packages/google/genai/`) — system_instruction support, GenerateContentConfig fields, mldev transformer
- `backend/app/services/ai_analysis_service.py` — all 4 prompt builders, retry logic, context gatherers, API call methods
- `backend/app/schemas/analysis.py` — all 4 batch response schemas
- `backend/app/config.py` — gemini_model, gemini_batch_size, temperature settings
- `backend/app/resilience.py` — circuit breaker pattern
- `backend/app/models/daily_price.py` — DailyPrice model with close column
- `backend/app/models/technical_indicator.py` — TechnicalIndicator model
- `backend/tests/test_ai_analysis_service.py` — existing test coverage

### Secondary (MEDIUM confidence)
- None needed — all findings verified from installed SDK and codebase

### Tertiary (LOW confidence)
- None

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries already installed and in use
- Architecture: HIGH — single-file modification, SDK API verified from source
- Pitfalls: MEDIUM — some assumptions about thinking model interaction and few-shot placement
- SDK behavior: HIGH — verified from actual installed source code

**Research date:** 2026-04-18
**Valid until:** 2026-05-18 (stable — SDK installed, codebase under our control)
