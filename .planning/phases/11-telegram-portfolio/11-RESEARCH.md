# Phase 11: Telegram Portfolio — Research

**Researched:** 2026-04-17
**Domain:** Telegram bot command handlers + PortfolioService integration
**Confidence:** HIGH

## Summary

This phase wires the existing Phase 8 PortfolioService to Telegram bot commands (`/buy`, `/sell`, `/portfolio`, `/pnl`) and enhances the daily summary with portfolio P&L context. The codebase is well-structured with clear patterns — every existing command handler follows the same template: parse `context.args`, open `async with async_session()`, call a service, format with `MessageFormatter`, and reply.

The main implementation gap is that PortfolioService lacks a per-ticker lot breakdown method (needed for `/pnl <ticker>` — TBOT-05). A `get_ticker_pnl(symbol)` method must be added that returns open lots with individual cost/P&L. Everything else is straightforward wiring — the patterns are established, the service API exists, and the formatter/handler architecture is clean.

**Primary recommendation:** Follow the exact handler pattern from `handlers.py` (arg parsing → `async_session()` → service call → formatter → reply). Add 4 new commands, 5-6 new formatter methods, one new PortfolioService method, and modify `daily_summary_send` to include portfolio data.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-11-01:** Use python-telegram-bot command handlers. Each command creates a Trade via PortfolioService (from Phase 8). Commands are thin wrappers that format results for Telegram.
- **D-11-02:** `/buy VNM 100 85000` records buy trade. `/sell VNM 50 90000` records sell and shows realized P&L. Optional: `/buy VNM 100 85000 150000` (with fee as 4th param). Simple positional arguments. Ticker validation against tickers table.
- **D-11-03:** Add portfolio P&L to daily_summary_send job. If user has positions, show portfolio value change alongside market summary. Sent at 16:00 with existing summary. Natural extension of daily_summary_send job.
- **D-11-04:** In daily summary, sort owned tickers to top of recommendations with position-specific P&L annotation.

### Copilot's Discretion
- Message formatting details (layout, emojis, Vietnamese text)
- Error message wording
- How to structure the new PortfolioService method for lot breakdown

### Deferred Ideas (OUT OF SCOPE)
- None — all TBOT-01 through TBOT-06 are in scope
</user_constraints>

<phase_requirements>

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| TBOT-01 | `/buy <ticker> <qty> <price>` command records a buy trade | PortfolioService.record_trade() with side="BUY" — existing API, needs handler + formatter |
| TBOT-02 | `/sell <ticker> <qty> <price>` command records a sell trade and shows realized P&L | PortfolioService.record_trade() with side="SELL" returns realized_pnl — needs handler + formatter |
| TBOT-03 | `/portfolio` command shows all holdings with current P&L | PortfolioService.get_holdings() + get_summary() — existing API, needs handler + formatter |
| TBOT-04 | Daily portfolio P&L notification sent at 16:00 alongside market summary | Modify AlertService.build_daily_summary() + MessageFormatter.daily_summary() |
| TBOT-05 | `/pnl <ticker>` command shows detailed P&L with FIFO lot breakdown | **NEEDS NEW METHOD** — PortfolioService has no per-ticker lot breakdown method |
| TBOT-06 | Daily summary highlights owned tickers first with position P&L context | Modify AlertService.build_daily_summary() to sort owned tickers first in recommendations |

</phase_requirements>

## Standard Stack

### Core (Already in Project)
| Library | Version | Purpose | Status |
|---------|---------|---------|--------|
| python-telegram-bot | 22.7 | Bot framework with CommandHandler, Update, ContextTypes | Already installed [VERIFIED: codebase] |
| SQLAlchemy async | 2.x | Database access via `async_session()` | Already installed [VERIFIED: codebase] |
| PortfolioService | Phase 8 | Trade recording, FIFO lots, P&L computation | Already implemented [VERIFIED: portfolio_service.py] |
| AlertService | Phase 4 | Daily summary build + send | Already implemented [VERIFIED: services.py] |
| MessageFormatter | Phase 3 | HTML message formatting for Telegram | Already implemented [VERIFIED: formatter.py] |

### No New Dependencies
This phase requires zero new packages. Everything is wiring existing code together.

## Architecture Patterns

### Established Command Handler Pattern
[VERIFIED: `backend/app/telegram/handlers.py`]

Every handler follows this exact structure:

```python
async def xxx_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/<command> — Description."""
    # 1. Parse & validate args
    if not context.args or len(context.args) != N:
        await update.message.reply_text(
            MessageFormatter.usage_error("/cmd", "/cmd EXAMPLE"),
            parse_mode="HTML",
        )
        return

    # 2. Extract and normalize args
    symbol = context.args[0].upper().strip()

    # 3. Database operation inside async_session
    async with async_session() as session:
        # ... service calls ...

    # 4. Reply with formatted message
    await update.message.reply_text(
        MessageFormatter.xxx(...), parse_mode="HTML"
    )
```

**Key details:**
- `context.args` is a `list[str]` — positional args split by space [VERIFIED: handlers.py]
- `async_session()` from `app.database` — context manager, creates fresh session [VERIFIED: database.py]
- `parse_mode="HTML"` — all messages use HTML, not MarkdownV2 [VERIFIED: formatter.py docstring]
- Chat ID via `str(update.effective_chat.id)` [VERIFIED: handlers.py]
- Error handling: catch `ValueError` from PortfolioService, reply with user-friendly message [VERIFIED: api/portfolio.py pattern]

### Handler Registration Pattern
[VERIFIED: `backend/app/telegram/handlers.py` lines 25-33]

```python
def register_handlers(app: Application) -> None:
    """Register all command handlers with the bot Application."""
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("buy", buy_command))     # NEW
    app.add_handler(CommandHandler("sell", sell_command))    # NEW
    app.add_handler(CommandHandler("portfolio", portfolio_command))  # NEW
    app.add_handler(CommandHandler("pnl", pnl_command))     # NEW
    # ... existing handlers ...
```

### MessageFormatter Pattern
[VERIFIED: `backend/app/telegram/formatter.py`]

All methods are `@staticmethod`, return `str` with HTML tags:
- `<b>bold</b>` for emphasis
- `<code>monospace</code>` for code/values
- `<i>italic</i>` for explanations
- Emojis for visual cues (🟢 gain, 🔴 loss, 📊 data)
- Vietnamese language throughout
- Numbers formatted with `,` thousands separator and `đ` suffix for VND

### PortfolioService Session Pattern
[VERIFIED: `backend/app/services/portfolio_service.py`]

Service receives session in constructor — NOT a singleton. Created per-request:

```python
async with async_session() as session:
    service = PortfolioService(session)
    result = await service.record_trade(...)
```

**Critical:** `record_trade()` calls `session.commit()` internally. The handler should NOT call commit again. [VERIFIED: portfolio_service.py line 76]

### Daily Summary Job Pattern
[VERIFIED: `backend/app/scheduler/jobs.py` lines 443-469]

```python
async def daily_summary_send():
    async with async_session() as session:
        job_svc = JobExecutionService(session)
        execution = await job_svc.start("daily_summary_send")
        try:
            service = AlertService(session)
            result = await service.send_daily_summary()
            await job_svc.complete(execution, ...)
            await session.commit()
        except Exception as e:
            await job_svc.complete(execution, status="partial", ...)
            await session.commit()
```

### Recommended New File Structure
```
backend/app/telegram/
├── __init__.py          # existing
├── bot.py               # existing — no changes needed
├── formatter.py         # MODIFY — add 5-6 new formatter methods
├── handlers.py          # MODIFY — add 4 new command handlers + update register_handlers
└── services.py          # MODIFY — enhance build_daily_summary with portfolio data
```

```
backend/app/services/
├── portfolio_service.py # MODIFY — add get_ticker_pnl() method
```

### Anti-Patterns to Avoid
- **Don't create a separate portfolio_handlers.py file:** All existing handlers are in `handlers.py`. Keep the single-file pattern. The file is ~350 lines, adding ~150 more is fine. [VERIFIED: current codebase pattern]
- **Don't call session.commit() in handlers:** PortfolioService.record_trade() already commits. Double-commit causes issues. [VERIFIED: portfolio_service.py line 76]
- **Don't use MarkdownV2 parse_mode:** All messages use HTML. MarkdownV2 has escape-character nightmares with numbers and special chars. [VERIFIED: formatter.py docstring]
- **Don't instantiate PortfolioService outside async_session context:** Session must be active during service calls. [VERIFIED: api/portfolio.py pattern]

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| FIFO P&L computation | Custom lot matching in handler | `PortfolioService.record_trade()` | Already handles FIFO lot consumption, validated with tests [VERIFIED: test_portfolio.py] |
| Ticker validation | Manual DB query in handler | `PortfolioService._resolve_ticker()` which raises `ValueError` | Already exists, consistent error handling [VERIFIED: portfolio_service.py line 281] |
| Sell validation | Manual remaining_qty check | `PortfolioService._validate_sell()` | Already validates and raises `ValueError` with clear message [VERIFIED: portfolio_service.py line 291] |
| Number formatting | `f"{x:,.0f}"` everywhere | Dedicated formatter method | Consistency with existing VND formatting patterns |

## PortfolioService API Reference

**Critical detail for handler implementation** — exact signatures and return shapes:

### `record_trade(symbol, side, quantity, price, trade_date, fees=0) → dict`
[VERIFIED: portfolio_service.py lines 25-88]

**Parameters:**
- `symbol: str` — ticker symbol (e.g., "VNM"), uppercased internally
- `side: str` — "BUY" or "SELL" (uppercased internally)
- `quantity: int` — number of shares
- `price: float` — price per share
- `trade_date: date` — trade date
- `fees: float` — total fees (default 0)

**Returns:**
```python
{
    "id": 1,
    "symbol": "VNM",
    "side": "BUY",
    "quantity": 100,
    "price": 85000.0,
    "fees": 0.0,
    "trade_date": "2024-01-15",
    "created_at": "2024-01-15T10:00:00",
    "realized_pnl": None,  # None for BUY, float for SELL
}
```

**Raises:** `ValueError` if ticker not found or sell exceeds available shares.

### `get_holdings() → list[dict]`
[VERIFIED: portfolio_service.py lines 90-163]

**Returns:**
```python
[
    {
        "symbol": "VNM",
        "name": "Vinamilk",
        "quantity": 100,
        "avg_cost": 85000.0,
        "market_price": 90000.0,
        "market_value": 9000000.0,
        "total_cost": 8500000.0,
        "unrealized_pnl": 500000.0,
        "unrealized_pnl_pct": 5.88,
    }
]
```

### `get_summary() → dict`
[VERIFIED: portfolio_service.py lines 165-227]

**Returns:**
```python
{
    "total_invested": 17000000.0,
    "total_market_value": 18500000.0,
    "total_realized_pnl": 500000.0,
    "total_unrealized_pnl": 1000000.0,
    "total_return_pct": 8.82,
    "holdings_count": 3,
}
```

### MISSING: `get_ticker_pnl(symbol) → dict` (MUST BE ADDED)

The `/pnl <ticker>` command (TBOT-05) needs a method that returns:
- Current holding for that ticker (qty, avg_cost, market_price, unrealized P&L)
- FIFO lot breakdown (each open lot's buy_date, buy_price, remaining_qty, lot P&L)
- Realized P&L from past sell trades on this ticker

**Implementation approach:** Query `Lot` table where `ticker_id=X AND remaining_quantity > 0`, join with `DailyPrice` for market price, and `Trade` table for realized totals. Similar to `get_holdings()` but filtered to one ticker and including lot-level detail.

## Common Pitfalls

### Pitfall 1: Double session.commit()
**What goes wrong:** Handler calls `session.commit()` after `PortfolioService.record_trade()` already committed. Can cause unexpected behavior.
**Why it happens:** Handlers for other commands (watch, alert) manually commit because they do raw SQL. Portfolio commands go through the service which commits internally.
**How to avoid:** Do NOT call `session.commit()` in buy/sell handlers. `record_trade()` does it. [VERIFIED: portfolio_service.py line 76]
**Warning signs:** "Session is in an invalid transaction state" errors.

### Pitfall 2: Decimal vs float in Telegram messages
**What goes wrong:** PortfolioService uses `Decimal` internally but returns `float` in dicts. Formatting `Decimal` with `f"{x:,.0f}"` works, but mixing types causes issues.
**Why it happens:** `record_trade()` converts to float in return dict (line 87), but `_consume_lots_fifo()` returns raw `Decimal`.
**How to avoid:** The handler receives float values from `record_trade()` return dict. Format as VND: `f"{price:,.0f}đ"`. The `realized_pnl` may be `None` (for BUY trades) — always check. [VERIFIED: portfolio_service.py line 87]
**Warning signs:** `TypeError: unsupported format character` or unexpected decimal places.

### Pitfall 3: trade_date parameter for Telegram commands
**What goes wrong:** The `record_trade()` method requires `trade_date: date`. The Telegram command syntax `"/buy VNM 100 85000"` doesn't include a date.
**Why it happens:** API has date as required field; Telegram UX should default to today.
**How to avoid:** In buy/sell handlers, default `trade_date=date.today()`. The API requires it explicitly, but Telegram can default. [VERIFIED: TradeRequest schema requires date, but Telegram UX should simplify]
**Warning signs:** `TypeError: missing required argument 'trade_date'`.

### Pitfall 4: Sell with no holdings — error message
**What goes wrong:** `PortfolioService._validate_sell()` raises `ValueError("Cannot sell X shares — only Y available")`. If not caught, the handler crashes silently.
**Why it happens:** Service raises, but handler doesn't wrap in try/except.
**How to avoid:** Wrap `PortfolioService.record_trade()` call in try/except ValueError. Format error as user-friendly Telegram message. [VERIFIED: api/portfolio.py lines 32-36 shows this pattern]

### Pitfall 5: Handler count in test assertion
**What goes wrong:** `test_register_handlers_adds_all_commands` asserts exactly 7 handlers. Adding 4 new handlers breaks this test.
**Why it happens:** Test has hardcoded handler count.
**How to avoid:** Update test to assert 11 handlers (7 existing + 4 new). Also update the expected commands set. [VERIFIED: test_telegram.py line 303]
**Warning signs:** Test failure "assert 11 == 7".

### Pitfall 6: Welcome message not updated
**What goes wrong:** `/start` shows the old command list without portfolio commands.
**Why it happens:** `MessageFormatter.welcome()` has hardcoded command list.
**How to avoid:** Update `welcome()` to include `/buy`, `/sell`, `/portfolio`, `/pnl`. [VERIFIED: formatter.py lines 13-26]

## Code Examples

### Buy Command Handler
```python
# Pattern derived from existing handlers [VERIFIED: handlers.py]
from datetime import date

async def buy_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/buy <ticker> <qty> <price> [fee] — Record a buy trade."""
    if not context.args or len(context.args) < 3:
        await update.message.reply_text(
            MessageFormatter.usage_error("/buy", "/buy VNM 100 85000"),
            parse_mode="HTML",
        )
        return

    symbol = context.args[0].upper().strip()
    try:
        quantity = int(context.args[1])
        price = float(context.args[2].replace(",", ""))
        fees = float(context.args[3].replace(",", "")) if len(context.args) > 3 else 0
    except (ValueError, IndexError):
        await update.message.reply_text(
            MessageFormatter.usage_error("/buy", "/buy VNM 100 85000"),
            parse_mode="HTML",
        )
        return

    async with async_session() as session:
        service = PortfolioService(session)
        try:
            result = await service.record_trade(
                symbol=symbol, side="BUY", quantity=quantity,
                price=price, trade_date=date.today(), fees=fees,
            )
        except ValueError as e:
            await update.message.reply_text(
                MessageFormatter.ticker_not_found(symbol), parse_mode="HTML"
            )
            return

    await update.message.reply_text(
        MessageFormatter.trade_recorded(result), parse_mode="HTML"
    )
```

### Formatter Methods — Trade Recorded
```python
# Pattern derived from existing formatter [VERIFIED: formatter.py]
@staticmethod
def trade_recorded(trade: dict) -> str:
    """Format trade confirmation for /buy or /sell."""
    side = trade["side"]
    emoji = "🟢" if side == "BUY" else "🔴"
    side_vn = "MUA" if side == "BUY" else "BÁN"
    price_str = f"{trade['price']:,.0f}đ"
    total = trade['price'] * trade['quantity']
    total_str = f"{total:,.0f}đ"

    lines = [
        f"{emoji} <b>{side_vn} {trade['symbol']}</b>",
        f"📊 SL: {trade['quantity']:,} | Giá: {price_str}",
        f"💰 Tổng: {total_str}",
    ]
    if trade.get("fees", 0) > 0:
        lines.append(f"🏦 Phí: {trade['fees']:,.0f}đ")

    # Show realized P&L for SELL trades
    if trade.get("realized_pnl") is not None:
        pnl = trade["realized_pnl"]
        pnl_emoji = "📈" if pnl >= 0 else "📉"
        lines.append(f"\n{pnl_emoji} <b>Lãi/Lỗ thực hiện: {pnl:+,.0f}đ</b>")

    return "\n".join(lines)
```

### Portfolio View Formatter
```python
@staticmethod
def portfolio_view(holdings: list[dict], summary: dict) -> str:
    """Format /portfolio response with all holdings + summary."""
    if not holdings:
        return "📋 Chưa có vị thế nào\n\n💡 Dùng /buy <mã> <SL> <giá> để ghi nhận giao dịch"

    lines = ["📊 <b>DANH MỤC ĐẦU TƯ</b>\n"]

    for h in holdings:
        pnl = h.get("unrealized_pnl")
        pnl_pct = h.get("unrealized_pnl_pct")
        emoji = "🟢" if (pnl or 0) >= 0 else "🔴"
        price_str = f"{h['market_price']:,.0f}đ" if h.get("market_price") else "—"
        pnl_str = f"{pnl:+,.0f}đ ({pnl_pct:+.1f}%)" if pnl is not None else "—"

        lines.append(
            f"{emoji} <b>{h['symbol']}</b> | {h['quantity']:,} cp\n"
            f"   Giá TB: {h['avg_cost']:,.0f}đ | Giá TT: {price_str}\n"
            f"   P&L: {pnl_str}"
        )

    # Summary section
    lines.append(f"\n{'─' * 25}")
    lines.append(f"💼 Tổng đầu tư: {summary['total_invested']:,.0f}đ")
    if summary.get("total_market_value") is not None:
        lines.append(f"💰 Giá trị TT: {summary['total_market_value']:,.0f}đ")
    if summary.get("total_unrealized_pnl") is not None:
        pnl = summary["total_unrealized_pnl"]
        emoji = "📈" if pnl >= 0 else "📉"
        lines.append(f"{emoji} Lãi/Lỗ chưa TH: {pnl:+,.0f}đ")
    if summary.get("total_realized_pnl", 0) != 0:
        lines.append(f"✅ Lãi/Lỗ đã TH: {summary['total_realized_pnl']:+,.0f}đ")
    if summary.get("total_return_pct") is not None:
        lines.append(f"📊 Tổng lợi nhuận: {summary['total_return_pct']:+.1f}%")

    return "\n".join(lines)
```

### Daily Summary Integration (TBOT-04 + TBOT-06)
```python
# In AlertService.build_daily_summary() — add portfolio section
# [VERIFIED: services.py build_daily_summary() returns a dict, daily_summary() formats it]

# 1. Add portfolio data to summary dict:
from app.services.portfolio_service import PortfolioService
portfolio_svc = PortfolioService(self.session)
holdings = await portfolio_svc.get_holdings()
if holdings:
    data["portfolio_holdings"] = holdings
    portfolio_summary = await portfolio_svc.get_summary()
    data["portfolio_summary"] = portfolio_summary
    # Extract owned ticker symbols for TBOT-06 sorting
    data["owned_symbols"] = {h["symbol"] for h in holdings}

# 2. In MessageFormatter.daily_summary() — add portfolio section after movers
# 3. Sort new_recommendations to put owned tickers first (TBOT-06)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Commands directly in bot.py | Separate handlers.py with register_handlers() | Phase 3 | All new commands go in handlers.py |
| Inline SQL queries | Service layer (PortfolioService, AlertService) | Phase 4/8 | Commands call services, don't query DB directly |

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest + pytest-asyncio |
| Config file | `backend/pytest.ini` |
| Quick run command | `cd backend && python -m pytest tests/test_telegram.py -x -q` |
| Full suite command | `cd backend && python -m pytest tests/ -x -q` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| TBOT-01 | /buy records trade | unit | `pytest tests/test_telegram.py::TestPortfolioCommands::test_buy_records_trade -x` | ❌ Wave 0 |
| TBOT-02 | /sell records trade + shows P&L | unit | `pytest tests/test_telegram.py::TestPortfolioCommands::test_sell_shows_pnl -x` | ❌ Wave 0 |
| TBOT-03 | /portfolio shows holdings | unit | `pytest tests/test_telegram.py::TestPortfolioCommands::test_portfolio_shows_holdings -x` | ❌ Wave 0 |
| TBOT-04 | Daily summary includes portfolio P&L | unit | `pytest tests/test_telegram.py::TestDailySummaryPortfolio::test_summary_includes_portfolio -x` | ❌ Wave 0 |
| TBOT-05 | /pnl shows lot breakdown | unit | `pytest tests/test_telegram.py::TestPortfolioCommands::test_pnl_shows_lots -x` | ❌ Wave 0 |
| TBOT-06 | Summary highlights owned tickers | unit | `pytest tests/test_telegram.py::TestDailySummaryPortfolio::test_owned_tickers_first -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `cd backend && python -m pytest tests/test_telegram.py -x -q`
- **Per wave merge:** `cd backend && python -m pytest tests/ -x -q`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] New test classes in `tests/test_telegram.py` — covers TBOT-01 through TBOT-06
- [ ] Tests for new formatter methods (trade_recorded, portfolio_view, ticker_pnl, daily_summary_portfolio)
- [ ] Tests for new PortfolioService.get_ticker_pnl() method
- [ ] Update `test_register_handlers_adds_all_commands` to expect 11 handlers

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `date.today()` for trade_date default is acceptable UX for Telegram (user can't specify date via command) | Common Pitfalls / Pitfall 3 | Low — user can always use API for historical trades |
| A2 | PortfolioService.get_ticker_pnl() should be a new public method, not assembled from existing private methods in the handler | Architecture Patterns | Low — could be done inline but service method is cleaner |

## Open Questions

1. **VND formatting consistency**
   - What we know: Existing formatters use `f"{x:,.0f}đ"` for prices. Some use `Decimal`, others `float`.
   - What's unclear: Whether portfolio values (millions of VND) should use abbreviated format (e.g., "8.5tr đ" for 8.5 triệu).
   - Recommendation: Use full number format like existing code. `8,500,000đ` is clear and consistent.

2. **Telegram message length limit**
   - What we know: Telegram max message length is 4096 characters [ASSUMED].
   - What's unclear: If user has 20+ holdings, /portfolio could exceed limit.
   - Recommendation: Truncate to top 15 holdings + "và X mã khác..." since this is single-user and unlikely to have that many. But add a safeguard.

## Sources

### Primary (HIGH confidence)
- `backend/app/telegram/handlers.py` — all 7 existing command handlers, registration pattern
- `backend/app/telegram/formatter.py` — all formatter methods, HTML/Vietnamese patterns
- `backend/app/telegram/services.py` — AlertService, build_daily_summary(), send_daily_summary()
- `backend/app/telegram/bot.py` — TelegramBot lifecycle, send_message()
- `backend/app/services/portfolio_service.py` — full API: record_trade, get_holdings, get_summary, get_trades
- `backend/app/scheduler/jobs.py` — daily_summary_send() job pattern
- `backend/app/scheduler/manager.py` — job scheduling, chaining, 16:00 cron
- `backend/app/database.py` — async_session pattern
- `backend/app/models/trade.py` — Trade model (side, quantity, price, fees, trade_date)
- `backend/app/models/lot.py` — Lot model (buy_price, quantity, remaining_quantity, buy_date)
- `backend/app/schemas/portfolio.py` — TradeRequest, HoldingResponse schemas
- `backend/tests/test_telegram.py` — existing test patterns, handler registration test
- `backend/tests/test_portfolio.py` — FIFO, P&L, trade recording tests

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all code is in the repo, verified via direct file reads
- Architecture: HIGH — patterns are consistent across 7 existing handlers
- Pitfalls: HIGH — identified from actual code analysis (double-commit, missing method, test count)
- PortfolioService API: HIGH — full method signatures and return shapes verified

**Research date:** 2026-04-17
**Valid until:** 2026-05-17 (stable codebase, no external dependency changes expected)
