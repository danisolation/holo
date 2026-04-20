# Phase 17: Enhanced Technical Indicators - Research

**Researched:** 2026-04-20
**Domain:** Technical indicator computation (ta library), database migration (Alembic), financial charting (lightweight-charts), accordion UI (shadcn)
**Confidence:** HIGH

## Summary

Phase 17 adds three new technical indicator families — ATR (volatility), ADX with +DI/-DI (trend strength), and Stochastic %K/%D (momentum) — to the existing indicator pipeline. The implementation follows a well-established pattern: the project already computes 12 indicators through `IndicatorService._compute_indicators()`, stores them in `technical_indicators` table via bulk upsert, exposes them via `GET /api/analysis/{symbol}/indicators`, and renders them as sub-charts in `indicator-chart.tsx`. Each layer needs extending, not inventing.

The critical technical finding is that the `ta` library's ATR and ADX classes produce `0.0` during their warm-up period instead of `NaN`. This differs from existing indicators (RSI, MACD) which produce proper `NaN` values. Without handling, these zeros will be stored as `Decimal('0')` in PostgreSQL and rendered as misleading flat lines on charts. The fix is straightforward: replace `0.0` with `NaN` before storage, matching the existing NULL-for-warm-up convention.

The backend `_compute_indicators()` method currently only accepts a `close` Series. ATR, ADX, and Stochastic all require `high` and `low` Series additionally. The `compute_for_ticker()` query must be extended to fetch `DailyPrice.high` and `DailyPrice.low`. This is a surgical change — 2 lines in the query, 1 line in the function signature.

**Primary recommendation:** Extend the existing indicator pipeline in-place following the exact patterns from Phase 2, add 6 nullable columns via migration 010, install shadcn Accordion, and add 3 new chart components matching RSI/MACD chart pattern.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- ATR window: 14 (industry standard, matches existing RSI-14)
- ADX window: 14 (Wilder's standard period)
- Stochastic window: 14 for %K, smoothing 3 for %D (standard parameters)
- Store ADX + +DI + -DI (all three) — +DI/-DI crossovers are critical for directional analysis in Phase 19
- Add new columns to existing technical_indicators table (not a separate table) — consistent with existing 12 indicators in same row per ticker/date
- Column precision: Numeric(12,4) — matches existing indicator columns (sma_20, bb_upper, etc.)
- Migration number: 010 (continues from 009 gemini_usage)
- New columns: atr_14, adx_14, plus_di_14, minus_di_14, stoch_k_14, stoch_d_14 (6 columns total)
- Each new indicator gets a separate sub-chart below candlestick, matching RSI/MACD chart pattern
- ATR: line chart showing volatility value
- ADX: line chart with ADX + reference line at 25 (strong trend threshold)
- Stochastic: %K/%D dual lines with 80/20 overbought/oversold zones
- Sub-charts use collapsible accordion — user picks which to show, avoids page bloat

### Agent's Discretion
- Chart colors for new indicators (follow existing color scheme) — UI SPEC decided: ATR amber, ADX cyan, +DI green, -DI red, %K pink, %D indigo
- Accordion default state — UI SPEC decided: RSI/MACD expanded, new indicators collapsed
- Sub-chart heights — UI SPEC decided: match existing 160px

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| SIG-01 | User can view ATR (Average True Range) indicator value for any ticker | `ta.volatility.AverageTrueRange` class verified: takes high/low/close/window=14, returns `.average_true_range()` Series. Warm-up produces 0.0 for first 13 rows (needs NaN replacement). Column `atr_14` Numeric(12,4). |
| SIG-02 | User can view ADX (trend strength) indicator value for any ticker | `ta.trend.ADXIndicator` class verified: takes high/low/close/window=14, returns `.adx()`, `.adx_pos()`, `.adx_neg()` Series. ADX warm-up is 27 rows (0.0), +DI/-DI warm-up is 15 rows (0.0). Columns: `adx_14`, `plus_di_14`, `minus_di_14` Numeric(12,4). |
| SIG-03 | User can view Stochastic oscillator value for any ticker | `ta.momentum.StochasticOscillator` class verified: takes high/low/close/window=14/smooth_window=3, returns `.stoch()` (%K) and `.stoch_signal()` (%D). %K warm-up 13 rows (NaN), %D warm-up 16 rows (NaN). Columns: `stoch_k_14`, `stoch_d_14` Numeric(12,4). |
</phase_requirements>

## Standard Stack

### Core (already installed, no new dependencies)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| ta | 0.11.0 | Technical indicator computation | Already in use for 12 indicators. ATR/ADX/Stochastic classes verified available. | [VERIFIED: pip show ta] |
| SQLAlchemy | ~2.0 | ORM for TechnicalIndicator model | Already in use. mapped_column for new Numeric columns. | [VERIFIED: codebase] |
| Alembic | ~1.18 | Migration 010 for new columns | Existing pattern from 001-009 migrations. | [VERIFIED: codebase] |
| lightweight-charts | 5.1.0 | Sub-chart rendering | Already in use for RSI/MACD charts. LineSeries for all new indicators. | [VERIFIED: package.json] |
| pandas | ~2.2 | DataFrame for high/low/close price data | Already in use. DataFrame column access unchanged. | [VERIFIED: codebase] |

### New Component (install required)

| Component | Source | Purpose | Install Command |
|-----------|--------|---------|-----------------|
| shadcn Accordion | shadcn registry | Collapsible wrapper for 5 indicator sub-charts | `npx shadcn@latest add accordion` |

**Note:** shadcn Accordion is based on `@base-ui/react` (already installed as ^1.4.0). The accordion component will be code-generated into `frontend/src/components/ui/accordion.tsx`. [VERIFIED: components.json shows style: base-nova, @base-ui/react in package.json]

## Architecture Patterns

### Backend Changes — Extending Existing Pipeline

```
backend/
├── alembic/versions/
│   └── 010_enhanced_indicators.py     # NEW: Add 6 columns to technical_indicators
├── app/models/
│   └── technical_indicator.py         # MODIFY: Add 6 mapped_column attributes
├── app/schemas/
│   └── analysis.py                    # MODIFY: Add 6 fields to IndicatorResponse
├── app/services/
│   └── indicator_service.py           # MODIFY: Extend _compute_indicators + compute_for_ticker
└── app/api/
    └── analysis.py                    # MODIFY: Add 6 fields to indicator response mapping
```

### Frontend Changes — Accordion + 3 New Charts

```
frontend/src/
├── components/
│   ├── ui/
│   │   └── accordion.tsx              # NEW: shadcn Accordion component
│   └── indicator-chart.tsx            # MODIFY: Add ATRChart, ADXChart, StochasticChart + Accordion wrapper
└── lib/
    └── api.ts                         # MODIFY: Add 6 fields to IndicatorData interface
```

### Pattern 1: Indicator Computation (extending _compute_indicators)
**What:** Add 3 new ta class instantiations returning 6 new Series to the indicator dict.
**When to use:** Backend computation layer.
**Current signature:** `_compute_indicators(self, close: pd.Series) -> dict[str, pd.Series]`
**New signature:** `_compute_indicators(self, close: pd.Series, high: pd.Series, low: pd.Series) -> dict[str, pd.Series]`

```python
# Source: verified against ta 0.11.0 class signatures [VERIFIED: inspect.signature]
from ta.volatility import AverageTrueRange
from ta.trend import ADXIndicator  # ADXIndicator already in ta.trend
from ta.momentum import StochasticOscillator

# Inside _compute_indicators, after existing indicators:
atr = AverageTrueRange(high=high, low=low, close=close, window=14, fillna=False)
adx_ind = ADXIndicator(high=high, low=low, close=close, window=14, fillna=False)
stoch = StochasticOscillator(high=high, low=low, close=close, window=14, smooth_window=3, fillna=False)

# CRITICAL: Replace warm-up 0.0 values with NaN for ATR/ADX/+DI/-DI
# These indicators produce 0.0 (not NaN) during warm-up, which would be stored
# as Decimal('0') instead of NULL. Use .replace(0.0, float('nan')).
return {
    # ... existing 12 indicators ...
    "atr_14": atr.average_true_range().replace(0.0, float('nan')),
    "adx_14": adx_ind.adx().replace(0.0, float('nan')),
    "plus_di_14": adx_ind.adx_pos().replace(0.0, float('nan')),
    "minus_di_14": adx_ind.adx_neg().replace(0.0, float('nan')),
    "stoch_k_14": stoch.stoch(),       # Already NaN during warm-up
    "stoch_d_14": stoch.stoch_signal(), # Already NaN during warm-up
}
```

### Pattern 2: Query Extension (compute_for_ticker)
**What:** Fetch high/low prices alongside close for the new indicators.
**Current query:**
```python
select(DailyPrice.date, DailyPrice.close)
```
**New query:**
```python
select(DailyPrice.date, DailyPrice.close, DailyPrice.high, DailyPrice.low)
```
**DataFrame construction changes:**
```python
df = pd.DataFrame(rows, columns=["date", "close", "high", "low"])
df["close"] = df["close"].astype(float)
df["high"] = df["high"].astype(float)
df["low"] = df["low"].astype(float)

indicators = self._compute_indicators(df["close"], df["high"], df["low"])
```

### Pattern 3: Migration (add columns)
**What:** Alembic migration 010 adds 6 nullable Numeric(12,4) columns.
```python
# Source: existing migration pattern from 001-009 [VERIFIED: codebase]
revision: str = "010"
down_revision: Union[str, None] = "009"

def upgrade() -> None:
    op.add_column("technical_indicators", sa.Column("atr_14", sa.Numeric(12, 4), nullable=True))
    op.add_column("technical_indicators", sa.Column("adx_14", sa.Numeric(12, 4), nullable=True))
    op.add_column("technical_indicators", sa.Column("plus_di_14", sa.Numeric(12, 4), nullable=True))
    op.add_column("technical_indicators", sa.Column("minus_di_14", sa.Numeric(12, 4), nullable=True))
    op.add_column("technical_indicators", sa.Column("stoch_k_14", sa.Numeric(12, 4), nullable=True))
    op.add_column("technical_indicators", sa.Column("stoch_d_14", sa.Numeric(12, 4), nullable=True))

def downgrade() -> None:
    op.drop_column("technical_indicators", "stoch_d_14")
    op.drop_column("technical_indicators", "stoch_k_14")
    op.drop_column("technical_indicators", "minus_di_14")
    op.drop_column("technical_indicators", "plus_di_14")
    op.drop_column("technical_indicators", "adx_14")
    op.drop_column("technical_indicators", "atr_14")
```

### Pattern 4: Frontend Chart Component (e.g., ATRChart)
**What:** Each new chart follows the exact RSIChart pattern from indicator-chart.tsx.
```typescript
// Source: existing RSIChart pattern [VERIFIED: indicator-chart.tsx lines 19-116]
function ATRChart({ indicatorData }: { indicatorData: IndicatorData[] }) {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const atrData = indicatorData
      .filter((d) => d.atr_14 != null)
      .map((d) => ({ time: d.date as string, value: d.atr_14! }))
      .sort((a, b) => (a.time as string).localeCompare(b.time as string));

    if (atrData.length === 0) return;

    const chart = createChart(container, {
      layout: { background: { color: "#0f172a" }, textColor: "#cbd5e1" },
      grid: { vertLines: { color: "#1e293b" }, horzLines: { color: "#1e293b" } },
      width: container.clientWidth,
      height: 160,
      rightPriceScale: { borderColor: "#334155", scaleMargins: { top: 0.1, bottom: 0.1 } },
      timeScale: { borderColor: "#334155", timeVisible: false },
      crosshair: { mode: 0 },
    });

    const atrSeries = chart.addSeries(LineSeries, {
      color: "#FBBF24",     // Amber — per UI SPEC
      lineWidth: 2,
      priceLineVisible: false,
      lastValueVisible: true,
    });
    atrSeries.setData(atrData);

    chart.timeScale().fitContent();

    const observer = new ResizeObserver((entries) => {
      for (const entry of entries) {
        chart.applyOptions({ width: entry.contentRect.width });
      }
    });
    observer.observe(container);

    return () => { observer.disconnect(); chart.remove(); };
  }, [indicatorData]);

  return (
    <div>
      <h4 className="text-xs font-medium text-muted-foreground mb-1 px-1">
        ATR (14)
        <span className="ml-2 text-[10px]">
          <span className="text-[#FBBF24]">Biến động giá</span>
        </span>
      </h4>
      <div ref={containerRef} className="rounded-lg overflow-hidden" />
    </div>
  );
}
```

### Pattern 5: Accordion Wrapper
**What:** Wrap all 5 indicator sub-charts in shadcn Accordion with `type="multiple"`.
```typescript
// Source: UI SPEC accordion behavior section [VERIFIED: 17-UI-SPEC.md]
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "@/components/ui/accordion";

export function IndicatorChart({ indicatorData }: IndicatorChartProps) {
  if (indicatorData.length === 0) {
    return (
      <div className="flex items-center justify-center h-40 text-muted-foreground text-sm">
        Không có dữ liệu chỉ báo kỹ thuật
      </div>
    );
  }

  return (
    <Accordion type="multiple" defaultValue={["rsi", "macd"]}>
      <AccordionItem value="rsi">
        <AccordionTrigger className="text-xs font-medium text-muted-foreground px-1">
          RSI (14) {/* + legend spans */}
        </AccordionTrigger>
        <AccordionContent>
          <RSIChart indicatorData={indicatorData} />
        </AccordionContent>
      </AccordionItem>
      {/* ... MACD, ATR, ADX, Stochastic items ... */}
    </Accordion>
  );
}
```

### Anti-Patterns to Avoid
- **Don't use a separate table for new indicators:** CONTEXT.md explicitly locks "same row per ticker/date" in existing `technical_indicators` table.
- **Don't call `_compute_indicators` with only `close`:** The new indicators require `high`/`low`. The method signature must be extended.
- **Don't store warm-up 0.0 values as Decimal(0):** Replace with NaN before storage. ATR/ADX produce misleading zeros that aren't real indicator values.
- **Don't create separate chart files:** UI SPEC specifies ATRChart, ADXChart, StochasticChart go into the existing `indicator-chart.tsx` file.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| ATR computation | Manual True Range + EMA calculation | `ta.volatility.AverageTrueRange` | Wilder's smoothing method is subtle; hand-rolled versions often use simple moving average instead of exponential | [VERIFIED: ta 0.11.0] |
| ADX computation | Manual +DM/-DM + smoothing + DX averaging | `ta.trend.ADXIndicator` | ADX requires 3 nested smoothing stages (True Range → +DI/-DI → DX → ADX). Error-prone. | [VERIFIED: ta 0.11.0] |
| Stochastic %K/%D | Manual highest-high / lowest-low over window | `ta.momentum.StochasticOscillator` | Edge cases: division by zero when H=L over window, smoothing of %D. Library handles all. | [VERIFIED: ta 0.11.0] |
| Collapsible accordion | Custom state management + animation | `npx shadcn@latest add accordion` | Handles keyboard navigation, ARIA attributes, smooth animation, multiple-open state. | [VERIFIED: UI SPEC] |
| Reference lines on charts | Custom canvas drawing | `chart.addSeries(LineSeries, {...})` with constant data | Existing pattern from RSI chart's overbought/oversold lines. Already tested with lightweight-charts v5.1.0. | [VERIFIED: indicator-chart.tsx] |

## Common Pitfalls

### Pitfall 1: ATR/ADX Warm-Up Produces 0.0, Not NaN
**What goes wrong:** The `ta` library's `AverageTrueRange`, `ADXIndicator.adx()`, `.adx_pos()`, `.adx_neg()` produce `0.0` (not `NaN`) during their warm-up period. The existing `_safe_decimal()` converts NaN→None but passes 0.0 through as `Decimal('0')`.
**Why it happens:** Internal implementation difference in the `ta` library — these indicators use `_check_fillna` differently from momentum indicators like RSI.
**How to avoid:** Call `.replace(0.0, float('nan'))` on ATR, ADX, +DI, -DI Series before returning from `_compute_indicators()`. This converts warm-up zeros to NaN, which `_safe_decimal` then stores as NULL.
**Warning signs:** Charts showing flat lines at 0 for the first 13-27 data points. ATR value of 0.0 is impossible with real price data.
**Verified:** [VERIFIED: tested with ta 0.11.0 — ATR warm-up 13 rows of 0.0, ADX warm-up 27 rows, +DI/-DI warm-up 15 rows, Stochastic uses proper NaN]

### Pitfall 2: _compute_indicators Signature Change Breaks Existing Call
**What goes wrong:** Adding `high` and `low` parameters to `_compute_indicators()` without updating the call site in `compute_for_ticker()`.
**Why it happens:** The method is called in one place (line 93) as `self._compute_indicators(df["close"])`.
**How to avoid:** Update both the signature AND the call site simultaneously. Also update the DataFrame construction to include high/low columns.
**Warning signs:** TypeError at runtime about missing required positional arguments.
**Verified:** [VERIFIED: indicator_service.py line 93]

### Pitfall 3: Forgetting to Update API Response Mapping
**What goes wrong:** New columns exist in DB and model, but the API endpoint `get_ticker_indicators()` doesn't map them to the response schema.
**Why it happens:** The response mapping in `analysis.py` (line 214-230) manually maps each column with `float(row.X) if row.X is not None else None`. New columns must be added to this mapping.
**How to avoid:** Update all 4 layers in sequence: migration → model → schema → API endpoint mapping.
**Warning signs:** New fields always return `null` from the API despite data being in the database.
**Verified:** [VERIFIED: backend/app/api/analysis.py lines 214-230]

### Pitfall 4: RSI/MACD Chart Labels Move Into Accordion Triggers
**What goes wrong:** Currently RSIChart and MACDChart have their own `<h4>` labels with color legends. When wrapping in Accordion, the label needs to move to `AccordionTrigger` to avoid duplicate headers.
**Why it happens:** The existing chart components render their own headers. Accordion adds another layer of trigger text.
**How to avoid:** Either: (a) remove the `<h4>` from existing RSIChart/MACDChart and put the label text in AccordionTrigger, or (b) keep chart labels inside AccordionContent and use minimal AccordionTrigger text. The cleaner approach is (a) — move labels to AccordionTrigger for consistency across all 5 charts.
**Warning signs:** Double headers (accordion trigger text + chart h4 text).
**Verified:** [VERIFIED: indicator-chart.tsx lines 105-115, 214-224]

### Pitfall 5: ADX Warm-Up Is Much Longer Than Other Indicators
**What goes wrong:** ADX requires 27 rows of warm-up before producing non-zero values, while +DI/-DI need 15 rows. This means for tickers with only 20-30 rows of price history, the ADX chart will be nearly empty while other indicators show data.
**Why it happens:** ADX is computed from smoothed +DI/-DI values, which are themselves smoothed from True Range — triple-nested smoothing.
**How to avoid:** The existing `min 20 rows` check in `compute_for_ticker()` is sufficient since 20 rows produces valid ATR and Stochastic data. ADX will naturally have NULLs for early dates, which the frontend handles gracefully (chart renders nothing when filtered data is empty).
**Warning signs:** ADX chart appearing empty while other indicator charts show data. This is expected behavior, not a bug.
**Verified:** [VERIFIED: tested — ADX first non-zero at index 27]

### Pitfall 6: Existing Indicator Upsert SET Clause Needs New Columns
**What goes wrong:** The bulk upsert in `compute_for_ticker()` uses `on_conflict_do_update` with a dynamically-built SET clause from the first row's keys. If the first row doesn't include the new columns (because they're NULL), the SET clause won't update them.
**Why it happens:** The code uses `set_={k: stmt.excluded[k] for k in bulk_rows[0] if k not in ("ticker_id", "date")}`.
**How to avoid:** This is actually NOT a problem — the new indicator Series are always included in the `indicators` dict (even as NaN/None). The loop at lines 115-116 always adds all columns to the values dict. `_safe_decimal(NaN)` returns `None`, which is included in the dict. So the SET clause will include all 18 columns. No change needed here.
**Warning signs:** N/A — verified safe.
**Verified:** [VERIFIED: indicator_service.py lines 111-117]

## Code Examples

### Example 1: Complete _compute_indicators Extension
```python
# Source: pattern from indicator_service.py + ta 0.11.0 verified API [VERIFIED]
def _compute_indicators(
    self, close: pd.Series, high: pd.Series, low: pd.Series
) -> dict[str, pd.Series]:
    """Pure computation — 18 indicators from close/high/low prices."""
    # Existing 12 indicators (unchanged)
    rsi = RSIIndicator(close=close, window=14, fillna=False)
    macd = MACD(close=close, window_slow=26, window_fast=12, window_sign=9, fillna=False)
    sma20 = SMAIndicator(close=close, window=20, fillna=False)
    sma50 = SMAIndicator(close=close, window=50, fillna=False)
    sma200 = SMAIndicator(close=close, window=200, fillna=False)
    ema12 = EMAIndicator(close=close, window=12, fillna=False)
    ema26 = EMAIndicator(close=close, window=26, fillna=False)
    bb = BollingerBands(close=close, window=20, window_dev=2, fillna=False)

    # New indicators (Phase 17)
    atr = AverageTrueRange(high=high, low=low, close=close, window=14, fillna=False)
    adx_ind = ADXIndicator(high=high, low=low, close=close, window=14, fillna=False)
    stoch = StochasticOscillator(
        high=high, low=low, close=close, window=14, smooth_window=3, fillna=False
    )

    return {
        # Existing 12
        "rsi_14": rsi.rsi(),
        "macd_line": macd.macd(),
        "macd_signal": macd.macd_signal(),
        "macd_histogram": macd.macd_diff(),
        "sma_20": sma20.sma_indicator(),
        "sma_50": sma50.sma_indicator(),
        "sma_200": sma200.sma_indicator(),
        "ema_12": ema12.ema_indicator(),
        "ema_26": ema26.ema_indicator(),
        "bb_upper": bb.bollinger_hband(),
        "bb_middle": bb.bollinger_mavg(),
        "bb_lower": bb.bollinger_lband(),
        # New 6 (Phase 17)
        # ATR/ADX produce 0.0 during warm-up — replace with NaN for NULL storage
        "atr_14": atr.average_true_range().replace(0.0, float('nan')),
        "adx_14": adx_ind.adx().replace(0.0, float('nan')),
        "plus_di_14": adx_ind.adx_pos().replace(0.0, float('nan')),
        "minus_di_14": adx_ind.adx_neg().replace(0.0, float('nan')),
        "stoch_k_14": stoch.stoch(),        # NaN during warm-up (correct)
        "stoch_d_14": stoch.stoch_signal(),  # NaN during warm-up (correct)
    }
```

### Example 2: Model Extension (6 New Columns)
```python
# Source: pattern from technical_indicator.py [VERIFIED: codebase]
# Add after bb_lower column (line 46):

# Volatility — ATR(14)
atr_14: Mapped[Decimal | None] = mapped_column(Numeric(12, 4), nullable=True)

# Trend — ADX(14)
adx_14: Mapped[Decimal | None] = mapped_column(Numeric(12, 4), nullable=True)
plus_di_14: Mapped[Decimal | None] = mapped_column(Numeric(12, 4), nullable=True)
minus_di_14: Mapped[Decimal | None] = mapped_column(Numeric(12, 4), nullable=True)

# Momentum — Stochastic(14, 3)
stoch_k_14: Mapped[Decimal | None] = mapped_column(Numeric(12, 4), nullable=True)
stoch_d_14: Mapped[Decimal | None] = mapped_column(Numeric(12, 4), nullable=True)
```

### Example 3: API Endpoint Response Mapping (6 New Fields)
```python
# Source: pattern from analysis.py lines 214-230 [VERIFIED: codebase]
# Add to the IndicatorResponse construction in get_ticker_indicators():
IndicatorResponse(
    # ... existing 12 fields ...
    atr_14=float(row.atr_14) if row.atr_14 is not None else None,
    adx_14=float(row.adx_14) if row.adx_14 is not None else None,
    plus_di_14=float(row.plus_di_14) if row.plus_di_14 is not None else None,
    minus_di_14=float(row.minus_di_14) if row.minus_di_14 is not None else None,
    stoch_k_14=float(row.stoch_k_14) if row.stoch_k_14 is not None else None,
    stoch_d_14=float(row.stoch_d_14) if row.stoch_d_14 is not None else None,
)
```

### Example 4: ADX Chart with 3 Lines + Reference Line
```typescript
// Source: RSIChart pattern + UI SPEC color specification [VERIFIED: indicator-chart.tsx, 17-UI-SPEC.md]
function ADXChart({ indicatorData }: { indicatorData: IndicatorData[] }) {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const adxData = indicatorData
      .filter((d) => d.adx_14 != null && d.plus_di_14 != null)
      .sort((a, b) => a.date.localeCompare(b.date));
    if (adxData.length === 0) return;

    const chart = createChart(container, { /* same config as RSI */ });

    // ADX line (cyan, primary)
    const adxLine = chart.addSeries(LineSeries, {
      color: "#06B6D4", lineWidth: 2,
      priceLineVisible: false, lastValueVisible: true,
    });
    adxLine.setData(adxData.map(d => ({ time: d.date as string, value: d.adx_14! })));

    // +DI line (green)
    const posLine = chart.addSeries(LineSeries, {
      color: "#22C55E", lineWidth: 1,
      priceLineVisible: false, lastValueVisible: false,
    });
    posLine.setData(adxData.map(d => ({ time: d.date as string, value: d.plus_di_14! })));

    // -DI line (red)
    const negLine = chart.addSeries(LineSeries, {
      color: "#EF4444", lineWidth: 1,
      priceLineVisible: false, lastValueVisible: false,
    });
    negLine.setData(adxData.map(d => ({ time: d.date as string, value: d.minus_di_14! })));

    // Reference line at 25 (strong trend threshold)
    const refLine = chart.addSeries(LineSeries, {
      color: "rgba(255,255,255,0.25)", lineWidth: 1, lineStyle: 2,
      priceLineVisible: false, lastValueVisible: false,
    });
    refLine.setData(adxData.map(d => ({ time: d.date as string, value: 25 })));

    chart.timeScale().fitContent();
    // ... ResizeObserver + cleanup (same pattern) ...
  }, [indicatorData]);

  return (
    <div>
      <h4 className="text-xs font-medium text-muted-foreground mb-1 px-1">
        ADX (14)
        <span className="ml-2 text-[10px]">
          <span className="text-[#06B6D4]">ADX</span>
          {" · "}<span className="text-[#22C55E]">+DI</span>
          {" · "}<span className="text-[#EF4444]">-DI</span>
          {" · "}<span className="text-white/25">25 xu hướng mạnh</span>
        </span>
      </h4>
      <div ref={containerRef} className="rounded-lg overflow-hidden" />
    </div>
  );
}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Custom ATR calculation with SMA | ta library's Wilder smoothing (EMA-based) | Standard since ta 0.11.0 | Wilder smoothing is the correct ATR method; SMA-based is a common error |
| ADX without DI lines | ADX + +DI + -DI for crossover analysis | Always standard (Wilder, 1978) | Phase 19 needs +DI/-DI crossovers for signal generation |
| All charts always visible | Accordion collapse for opt-in display | This phase (v3.0) | Prevents page bloat with 5 sub-charts below candlestick |

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 8.4.2 with pytest-asyncio |
| Config file | `backend/pytest.ini` (asyncio_mode = auto) |
| Quick run command | `cd backend && .venv/Scripts/python.exe -m pytest tests/test_indicator_service.py -x` |
| Full suite command | `cd backend && .venv/Scripts/python.exe -m pytest tests/ -x` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SIG-01 | ATR computation returns valid Series with NaN warm-up | unit | `pytest tests/test_indicator_service.py::TestComputeIndicators::test_returns_18_indicators -x` | ❌ Wave 0 (extend existing test) |
| SIG-01 | ATR warm-up 0.0→NaN replacement | unit | `pytest tests/test_indicator_service.py::TestComputeIndicators::test_atr_warmup_is_nan -x` | ❌ Wave 0 |
| SIG-02 | ADX/+DI/-DI computation returns valid Series | unit | `pytest tests/test_indicator_service.py::TestComputeIndicators::test_adx_series_valid -x` | ❌ Wave 0 |
| SIG-02 | ADX warm-up 0.0→NaN replacement | unit | `pytest tests/test_indicator_service.py::TestComputeIndicators::test_adx_warmup_is_nan -x` | ❌ Wave 0 |
| SIG-03 | Stochastic %K/%D computation returns valid Series | unit | `pytest tests/test_indicator_service.py::TestComputeIndicators::test_stochastic_series_valid -x` | ❌ Wave 0 |
| ALL | API response includes 6 new fields | unit | `pytest tests/test_indicator_service.py::TestIndicatorResponseSchema -x` | ❌ Wave 0 |
| ALL | _compute_indicators returns 18 indicators (was 12) | unit | `pytest tests/test_indicator_service.py::TestComputeIndicators::test_returns_18_indicators -x` | ❌ Wave 0 (update existing test_returns_12_indicators) |

### Sampling Rate
- **Per task commit:** `cd backend && .venv/Scripts/python.exe -m pytest tests/test_indicator_service.py -x`
- **Per wave merge:** `cd backend && .venv/Scripts/python.exe -m pytest tests/ -x`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] Update `test_returns_12_indicators` → `test_returns_18_indicators` with 6 new keys
- [ ] Add `test_atr_warmup_is_nan` — verify ATR warm-up 0.0 replaced with NaN
- [ ] Add `test_adx_warmup_is_nan` — verify ADX/+DI/-DI warm-up 0.0 replaced with NaN
- [ ] Add `test_stochastic_warmup_produces_nan` — verify %K NaN for first 13 rows, %D for first 15
- [ ] Add `test_compute_indicators_requires_high_low` — verify new signature works with high/low Series
- [ ] Update `test_series_length_matches_input` to include high/low params

## Security Domain

> This phase adds read-only data display with no user input, authentication, or external API changes. Security surface is minimal.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | N/A — no auth changes |
| V3 Session Management | no | N/A — no session changes |
| V4 Access Control | no | N/A — no new endpoints with different access |
| V5 Input Validation | no | Existing `limit` param validation unchanged; new fields are computed server-side |
| V6 Cryptography | no | N/A |

### Known Threat Patterns

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| SQL injection via migration | Tampering | Alembic `op.add_column` uses parameterized DDL — no raw SQL injection risk |

## Assumptions Log

> List all claims tagged `[ASSUMED]` in this research.

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| — | — | — | — |

**All claims in this research were verified via codebase inspection and `ta` library testing.** No user confirmation needed.

## Open Questions

1. **Existing indicator data backfill after migration**
   - What we know: Migration 010 adds 6 nullable columns. Existing rows will have NULL for new indicators.
   - What's unclear: Should we trigger a full recompute for all tickers after migration to populate the new columns? The incremental logic only computes new dates (after `last_computed`).
   - Recommendation: After running migration 010, trigger a one-time full recompute by either: (a) temporarily setting `indicator_compute_days` to cover the full history, or (b) resetting `last_computed` tracking. The simplest approach is option (a) since the compute_for_ticker loop already handles all 18 indicators for any date range. However, the incremental check (`last_computed`) means rows that already exist won't be recomputed. The upsert pattern handles this — it will UPDATE existing rows with the new column values. So just triggering a manual `/api/analysis/trigger/indicators` POST after migration should work, since `compute_days=60` covers recent data and the upsert SET clause includes all columns.

## Sources

### Primary (HIGH confidence)
- `ta` 0.11.0 API: `AverageTrueRange.__init__(high, low, close, window=14, fillna=False)` → `.average_true_range()` [VERIFIED: inspect.signature + runtime test]
- `ta` 0.11.0 API: `ADXIndicator.__init__(high, low, close, window=14, fillna=False)` → `.adx()`, `.adx_pos()`, `.adx_neg()` [VERIFIED: inspect.signature + runtime test]
- `ta` 0.11.0 API: `StochasticOscillator.__init__(high, low, close, window=14, smooth_window=3, fillna=False)` → `.stoch()`, `.stoch_signal()` [VERIFIED: inspect.signature + runtime test]
- Warm-up behavior: ATR 13 rows 0.0, ADX 27 rows 0.0, +DI/-DI 15 rows 0.0, Stoch %K 13 rows NaN, %D 16 rows NaN [VERIFIED: runtime test with n=50 sample data]
- Existing codebase: indicator_service.py, technical_indicator.py, analysis.py (API + schema), indicator-chart.tsx, api.ts [VERIFIED: file inspection]
- `@base-ui/react` ^1.4.0 already installed [VERIFIED: package.json]
- shadcn accordion available via `npx shadcn@latest add accordion` [VERIFIED: components.json style=base-nova]
- lightweight-charts 5.1.0 with LineSeries API [VERIFIED: package.json + indicator-chart.tsx usage]

### Secondary (MEDIUM confidence)
- None — all claims verified against codebase and runtime.

### Tertiary (LOW confidence)
- None.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries already in use, versions verified
- Architecture: HIGH — extending existing pattern with exact same conventions
- Pitfalls: HIGH — warm-up behavior tested empirically with actual ta 0.11.0 library
- Frontend patterns: HIGH — RSIChart/MACDChart provide exact template to follow

**Research date:** 2026-04-20
**Valid until:** 2026-06-20 (60 days — stable libraries, no major version changes expected)
