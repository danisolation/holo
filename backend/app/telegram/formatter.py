"""Message formatting for Telegram bot responses.

All messages use HTML parse_mode (not MarkdownV2 per CONTEXT.md D-2.4).
Vietnamese language with emojis for mobile-friendly reading.
"""
from decimal import Decimal

# Vietnamese labels for corporate event types (CORP-07)
EVENT_TYPE_LABELS = {
    "CASH_DIVIDEND": "Cổ tức tiền mặt",
    "STOCK_DIVIDEND": "Cổ tức cổ phiếu",
    "BONUS_SHARES": "Thưởng cổ phiếu",
    "RIGHTS_ISSUE": "Phát hành quyền mua",
}


class MessageFormatter:
    """Formats trading data into Telegram HTML messages."""

    @staticmethod
    def welcome() -> str:
        """Welcome message for /start command."""
        return (
            "🤖 <b>Holo — Stock Intelligence Bot</b>\n\n"
            "Xin chào! Tôi là bot phân tích cổ phiếu HOSE.\n\n"
            "📋 <b>Lệnh có sẵn:</b>\n"
            "/watch &lt;mã&gt; — Theo dõi mã cổ phiếu\n"
            "/unwatch &lt;mã&gt; — Bỏ theo dõi\n"
            "/list — Xem danh sách theo dõi\n"
            "/check &lt;mã&gt; — Kiểm tra phân tích mã\n"
            "/summary — Tóm tắt thị trường hôm nay\n"
            "/buy &lt;mã&gt; &lt;SL&gt; &lt;giá&gt; — Ghi nhận mua\n"
            "/sell &lt;mã&gt; &lt;SL&gt; &lt;giá&gt; — Ghi nhận bán\n"
            "/portfolio — Xem danh mục đầu tư\n"
            "/pnl &lt;mã&gt; — Chi tiết P&amp;L theo mã\n\n"
            "💡 Ví dụ: <code>/buy VNM 100 85000</code>"
        )

    @staticmethod
    def watch_added(symbol: str) -> str:
        """Confirmation for /watch command."""
        return f"✅ Đã thêm <b>{symbol}</b> vào danh sách theo dõi"

    @staticmethod
    def watch_exists(symbol: str) -> str:
        """Already watching message."""
        return f"ℹ️ <b>{symbol}</b> đã có trong danh sách theo dõi"

    @staticmethod
    def watch_removed(symbol: str) -> str:
        """Confirmation for /unwatch command."""
        return f"🗑 Đã xóa <b>{symbol}</b> khỏi danh sách theo dõi"

    @staticmethod
    def watch_not_found(symbol: str) -> str:
        """Not in watchlist message."""
        return f"⚠️ <b>{symbol}</b> không có trong danh sách theo dõi"

    @staticmethod
    def ticker_not_found(symbol: str) -> str:
        """Ticker doesn't exist in database."""
        return f"❌ Không tìm thấy mã <b>{symbol}</b> trên HOSE"

    @staticmethod
    def watchlist(items: list[dict]) -> str:
        """Format watchlist for /list command.

        Args:
            items: list of dicts with keys: symbol, signal, score, close
        """
        if not items:
            return "📋 Danh sách theo dõi trống\n\n💡 Dùng /watch &lt;mã&gt; để thêm"

        lines = ["📋 <b>Danh sách theo dõi</b>\n"]
        for item in items:
            signal_emoji = MessageFormatter._signal_emoji(item.get("signal", ""))
            close_str = f"{item['close']:,.0f}" if item.get("close") else "—"
            signal_str = item.get("signal", "—")
            score_str = f"{item.get('score', '—')}/10" if item.get("score") else "—"
            lines.append(
                f"{signal_emoji} <b>{item['symbol']}</b> | "
                f"{close_str}đ | {signal_str} ({score_str})"
            )
        return "\n".join(lines)

    @staticmethod
    def ticker_summary(data: dict) -> str:
        """Format on-demand ticker summary for /check command.

        Args:
            data: dict with keys: symbol, name, close, change_pct, volume,
                  technical_signal, technical_score, fundamental_signal, fundamental_score,
                  sentiment_signal, sentiment_score, combined_signal, combined_score,
                  combined_reasoning
        """
        symbol = data.get("symbol", "?")
        name = data.get("name", "")
        close = data.get("close")
        close_str = f"{close:,.0f}đ" if close else "—"
        change = data.get("change_pct")
        change_str = f"{change:+.1f}%" if change is not None else ""
        vol = data.get("volume")
        vol_str = f"{vol:,.0f}" if vol else "—"

        lines = [
            f"📊 <b>{symbol}</b> — {name}",
            f"💰 Giá: {close_str} {change_str}",
            f"📈 Khối lượng: {vol_str}\n",
        ]

        # Analysis dimensions
        for label, sig_key, score_key in [
            ("Kỹ thuật", "technical_signal", "technical_score"),
            ("Cơ bản", "fundamental_signal", "fundamental_score"),
            ("Tin tức", "sentiment_signal", "sentiment_score"),
        ]:
            sig = data.get(sig_key, "—")
            score = data.get(score_key)
            emoji = MessageFormatter._signal_emoji(sig)
            score_str = f"{score}/10" if score else "—"
            lines.append(f"{emoji} {label}: {sig} ({score_str})")

        # Combined recommendation (highlighted)
        combined = data.get("combined_signal")
        if combined:
            combined_emoji = MessageFormatter._recommendation_emoji(combined)
            combined_score = data.get("combined_score", "—")
            lines.append(f"\n{combined_emoji} <b>Khuyến nghị: {combined.upper()}</b> ({combined_score}/10)")
            reasoning = data.get("combined_reasoning", "")
            if reasoning:
                # Truncate to ~200 chars for mobile readability
                if len(reasoning) > 200:
                    reasoning = reasoning[:197] + "..."
                lines.append(f"<i>{reasoning}</i>")

        return "\n".join(lines)

    @staticmethod
    def signal_change(symbol: str, old_signal: str, new_signal: str, score: int, reasoning: str) -> str:
        """Signal change alert notification."""
        emoji = MessageFormatter._recommendation_emoji(new_signal)
        return (
            f"📡 <b>THAY ĐỔI TÍN HIỆU</b>\n\n"
            f"<b>{symbol}</b>: {old_signal} → <b>{new_signal.upper()}</b> {emoji}\n"
            f"💪 Độ tin cậy: {score}/10\n"
            f"<i>{reasoning[:200]}</i>"
        )

    @staticmethod
    def daily_summary(data: dict) -> str:
        """Format daily market summary for /summary and scheduled send.

        Args:
            data: dict with keys:
                - date: str
                - top_movers: list of {symbol, close, change_pct}
                - watchlist_changes: list of {symbol, old_signal, new_signal}
                - new_recommendations: list of {symbol, signal, score, reasoning}
                - total_tickers: int
                - analyzed_count: int
        """
        d = data.get("date", "")
        lines = [f"📰 <b>TÓM TẮT THỊ TRƯỜNG — {d}</b>\n"]

        # Top movers
        movers = data.get("top_movers", [])
        if movers:
            lines.append("🔥 <b>Top biến động:</b>")
            for m in movers[:5]:
                change = m.get("change_pct", 0)
                emoji = "🟢" if change > 0 else "🔴" if change < 0 else "⚪"
                close_str = f"{m['close']:,.0f}đ" if m.get("close") else "—"
                lines.append(f"  {emoji} <b>{m['symbol']}</b>: {close_str} ({change:+.1f}%)")
            lines.append("")

        # Portfolio P&L section (TBOT-04)
        portfolio = data.get("portfolio_holdings", [])
        portfolio_summary = data.get("portfolio_summary", {})
        if portfolio:
            lines.append("💼 <b>Danh mục của bạn:</b>")
            for h in portfolio:
                pnl = h.get("unrealized_pnl")
                pnl_pct = h.get("unrealized_pnl_pct")
                emoji = "🟢" if (pnl or 0) >= 0 else "🔴"
                price_str = f"{h['market_price']:,.0f}đ" if h.get("market_price") else "—"
                pnl_str = f"{pnl:+,.0f}đ ({pnl_pct:+.1f}%)" if pnl is not None else "—"
                lines.append(f"  {emoji} <b>{h['symbol']}</b>: {price_str} | P&L: {pnl_str}")

            total_upnl = portfolio_summary.get("total_unrealized_pnl")
            if total_upnl is not None:
                total_emoji = "📈" if total_upnl >= 0 else "📉"
                lines.append(f"  {total_emoji} Tổng P&L: {total_upnl:+,.0f}đ")
                return_pct = portfolio_summary.get("total_return_pct")
                if return_pct is not None:
                    lines.append(f"  📊 Lợi nhuận: {return_pct:+.1f}%")
            lines.append("")

        # Watchlist signal changes
        changes = data.get("watchlist_changes", [])
        if changes:
            lines.append("📡 <b>Thay đổi tín hiệu watchlist:</b>")
            for c in changes:
                emoji = MessageFormatter._recommendation_emoji(c.get("new_signal", ""))
                lines.append(
                    f"  {emoji} <b>{c['symbol']}</b>: {c.get('old_signal', '—')} → {c.get('new_signal', '—')}"
                )
            lines.append("")

        # New strong recommendations (TBOT-06: owned tickers first)
        recs = data.get("new_recommendations", [])
        if recs:
            owned_symbols = data.get("owned_symbols", set())
            owned_recs = [r for r in recs if r.get("symbol") in owned_symbols]
            other_recs = [r for r in recs if r.get("symbol") not in owned_symbols]
            sorted_recs = owned_recs + other_recs

            lines.append("💡 <b>Khuyến nghị mới:</b>")
            for r in sorted_recs[:5]:
                emoji = MessageFormatter._recommendation_emoji(r.get("signal", ""))
                symbol = r.get("symbol", "?")
                owned_tag = " 📌" if symbol in owned_symbols else ""
                lines.append(
                    f"  {emoji} <b>{symbol}</b>{owned_tag}: "
                    f"{r.get('signal', '—')} ({r.get('score', '—')}/10)"
                )
            lines.append("")

        total = data.get("total_tickers", 0)
        analyzed = data.get("analyzed_count", 0)
        lines.append(f"📊 Đã phân tích: {analyzed}/{total} mã")

        return "\n".join(lines)

    @staticmethod
    def usage_error(command: str, usage: str) -> str:
        """Usage error message."""
        return f"⚠️ Sai cú pháp\n\n💡 Dùng: <code>{usage}</code>"

    @staticmethod
    def job_failure_alert(job_name: str, error_summary: str) -> str:
        """Format critical job failure notification (D-12).
        error_summary is pre-truncated by caller."""
        import html
        safe_error = html.escape(error_summary[:300])
        return (
            f"⚠️ <b>JOB FAILED</b>\n\n"
            f"<b>{html.escape(job_name)}</b>\n"
            f"<code>{safe_error}</code>"
        )

    @staticmethod
    def circuit_open_alert(api_name: str, fail_count: int) -> str:
        """Format circuit breaker open notification (D-12)."""
        import html
        return (
            f"🔴 <b>CIRCUIT OPEN</b>\n\n"
            f"<b>{html.escape(api_name)}</b> — {fail_count} consecutive failures\n"
            f"Auto-reset after 2 minutes"
        )

    @staticmethod
    def exdate_alert(symbol: str, event_type: str, ex_date: str, detail: str = "") -> str:
        """Format ex-date alert notification (CORP-07).

        Args:
            symbol: Ticker symbol (e.g., VNM)
            event_type: CASH_DIVIDEND, STOCK_DIVIDEND, BONUS_SHARES, RIGHTS_ISSUE
            ex_date: Ex-date string (YYYY-MM-DD)
            detail: Optional detail line (dividend amount or ratio)
        """
        label = EVENT_TYPE_LABELS.get(event_type, event_type)
        msg = (
            f"📅 <b>Ex-date sắp tới</b>\n\n"
            f"<b>{symbol}</b> — {label}\n"
            f"📆 Ngày GDKHQ: <b>{ex_date}</b>"
        )
        if detail:
            msg += f"\n📋 {detail}"
        return msg

    @staticmethod
    def trade_recorded(trade: dict) -> str:
        """Format buy/sell confirmation message."""
        side = trade.get("side", "BUY")
        is_buy = side.upper() == "BUY"
        emoji = "🟢" if is_buy else "🔴"
        side_vn = "MUA" if is_buy else "BÁN"
        symbol = trade.get("symbol", "?")
        qty = trade.get("quantity", 0)
        price = trade.get("price", 0)
        total = qty * price
        fees = trade.get("fees", 0)

        lines = [
            f"{emoji} <b>{side_vn} — {symbol}</b>",
            f"📦 Số lượng: {qty:,} cp",
            f"💰 Giá: {price:,.0f}đ",
            f"💵 Tổng: {total:,.0f}đ",
        ]

        if fees and fees > 0:
            lines.append(f"🏷 Phí: {fees:,.0f}đ")

        realized_pnl = trade.get("realized_pnl")
        if realized_pnl is not None:
            pnl_emoji = "📈" if realized_pnl >= 0 else "📉"
            lines.append(f"{pnl_emoji} Lãi/Lỗ thực hiện: {realized_pnl:+,.0f}đ")

        return "\n".join(lines)

    @staticmethod
    def portfolio_view(holdings: list[dict], summary: dict) -> str:
        """Format /portfolio response with all holdings and summary."""
        if not holdings:
            return "📋 Chưa có vị thế nào\n\n💡 Dùng /buy &lt;mã&gt; &lt;SL&gt; &lt;giá&gt; để ghi nhận giao dịch"

        lines = ["💼 <b>DANH MỤC ĐẦU TƯ</b>\n"]

        for h in holdings:
            pnl = h.get("unrealized_pnl")
            pnl_pct = h.get("unrealized_pnl_pct")
            emoji = "🟢" if (pnl or 0) >= 0 else "🔴"
            price_str = f"{h['market_price']:,.0f}đ" if h.get("market_price") else "—"
            pnl_str = f"{pnl:+,.0f}đ ({pnl_pct:+.1f}%)" if pnl is not None else "—"
            lines.append(
                f"{emoji} <b>{h['symbol']}</b>: {h['quantity']:,} cp | "
                f"TB: {h['avg_cost']:,.0f}đ | Giá: {price_str}\n"
                f"   P&L: {pnl_str}"
            )

        lines.append("\n" + "─" * 24)
        total_invested = summary.get("total_invested", 0)
        total_mv = summary.get("total_market_value")
        total_upnl = summary.get("total_unrealized_pnl")
        total_rpnl = summary.get("total_realized_pnl", 0)
        total_return = summary.get("total_return_pct")

        lines.append(f"💰 Đầu tư: {total_invested:,.0f}đ")
        if total_mv is not None:
            lines.append(f"📊 Giá trị: {total_mv:,.0f}đ")
        if total_upnl is not None:
            upnl_emoji = "📈" if total_upnl >= 0 else "📉"
            lines.append(f"{upnl_emoji} Chưa thực hiện: {total_upnl:+,.0f}đ")
        lines.append(f"✅ Đã thực hiện: {total_rpnl:+,.0f}đ")
        if total_return is not None:
            lines.append(f"📊 Tổng lợi nhuận: {total_return:+.1f}%")

        return "\n".join(lines)

    @staticmethod
    def ticker_pnl(data: dict) -> str:
        """Format /pnl response with FIFO lot breakdown."""
        lots = data.get("lots", [])
        quantity = data.get("quantity", 0)
        symbol = data.get("symbol", "?")

        if not lots and quantity == 0:
            return f"📋 Không có vị thế <b>{symbol}</b>"

        name = data.get("name", "")
        avg_cost = data.get("avg_cost", 0)
        market_price = data.get("market_price")
        unrealized_pnl = data.get("unrealized_pnl")
        unrealized_pnl_pct = data.get("unrealized_pnl_pct")
        realized_pnl = data.get("realized_pnl", 0)

        price_str = f"{market_price:,.0f}đ" if market_price is not None else "—"
        upnl_str = f"{unrealized_pnl:+,.0f}đ ({unrealized_pnl_pct:+.1f}%)" if unrealized_pnl is not None else "—"

        lines = [
            f"📊 <b>CHI TIẾT P&L — {symbol}</b>",
            f"{name}\n",
            f"📦 Số lượng: {quantity:,} cp",
            f"💰 Giá TB: {avg_cost:,.0f}đ",
            f"📈 Giá TT: {price_str}",
            f"💹 P&L chưa thực hiện: {upnl_str}\n",
            "📦 <b>Lô FIFO:</b>",
        ]

        for i, lot in enumerate(lots, 1):
            buy_date = lot.get("buy_date", "?")
            buy_price = lot.get("buy_price", 0)
            remaining = lot.get("remaining", 0)
            original = lot.get("quantity", 0)
            lot_pnl = lot.get("lot_pnl")
            lot_pnl_str = f"{lot_pnl:+,.0f}đ" if lot_pnl is not None else "—"
            emoji = "🟢" if (lot_pnl or 0) >= 0 else "🔴"
            lines.append(
                f"  {emoji} Lô {i}: {buy_date} | {buy_price:,.0f}đ | "
                f"{remaining}/{original} cp | P&L: {lot_pnl_str}"
            )

        rpnl_emoji = "📈" if realized_pnl >= 0 else "📉"
        lines.append(f"\n{rpnl_emoji} Lãi/Lỗ đã thực hiện: {realized_pnl:+,.0f}đ")

        return "\n".join(lines)

    @staticmethod
    def _signal_emoji(signal: str) -> str:
        """Map signal/recommendation to emoji."""
        mapping = {
            "strong_buy": "🟢",
            "buy": "🟢",
            "mua": "🟢",
            "strong": "🟢",
            "good": "🟢",
            "very_positive": "🟢",
            "positive": "🟢",
            "neutral": "🟡",
            "giu": "🟡",
            "sell": "🔴",
            "strong_sell": "🔴",
            "ban": "🔴",
            "weak": "🔴",
            "critical": "🔴",
            "negative": "🔴",
            "very_negative": "🔴",
        }
        return mapping.get(signal.lower() if signal else "", "⚪")

    @staticmethod
    def _recommendation_emoji(signal: str) -> str:
        """Map combined recommendation to highlighted emoji."""
        mapping = {
            "mua": "🟢🟢",
            "giu": "🟡",
            "ban": "🔴🔴",
        }
        return mapping.get(signal.lower() if signal else "", "⚪")

    @staticmethod
    def health_alert(alert_type: str, details: list[str]) -> str:
        """Format health alert notification for Telegram (D-15-07).

        Vietnamese HTML message with severity emoji.
        Args:
            alert_type: "job_failures", "stale_data", "pool_exhaustion"
            details: List of affected items descriptions
        """
        import html as html_mod

        type_config = {
            "job_failures": {
                "emoji": "🔴",
                "title": "LỖI PIPELINE LIÊN TỤC",
                "severity": "critical",
            },
            "stale_data": {
                "emoji": "🟡",
                "title": "DỮ LIỆU CŨ",
                "severity": "warning",
            },
            "pool_exhaustion": {
                "emoji": "🔴",
                "title": "DB POOL CẠN KIỆT",
                "severity": "critical",
            },
        }

        config = type_config.get(alert_type, {
            "emoji": "⚠️",
            "title": alert_type.upper(),
            "severity": "warning",
        })

        lines = [
            f"{config['emoji']} <b>{config['title']}</b>\n",
        ]
        for item in details:
            lines.append(f"  • {html_mod.escape(item)}")

        lines.append(f"\n(Xem chi tiết: /dashboard/health)")

        return "\n".join(lines)
