"""Message formatting for Telegram bot responses.

All messages use HTML parse_mode (not MarkdownV2 per CONTEXT.md D-2.4).
Vietnamese language with emojis for mobile-friendly reading.
"""
from decimal import Decimal


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
            "/alert &lt;mã&gt; &lt;giá&gt; — Đặt cảnh báo giá\n"
            "/summary — Tóm tắt thị trường hôm nay\n\n"
            "💡 Ví dụ: <code>/watch VNM</code>"
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
    def alert_created(symbol: str, price: Decimal, direction: str) -> str:
        """Confirmation for /alert command."""
        dir_text = "vượt lên" if direction == "up" else "giảm xuống"
        emoji = "🔔" if direction == "up" else "🔕"
        return f"{emoji} Đặt cảnh báo: <b>{symbol}</b> {dir_text} <b>{price:,.0f}đ</b>"

    @staticmethod
    def alert_triggered(symbol: str, current_price: Decimal, target_price: Decimal, direction: str) -> str:
        """Alert notification when price threshold crossed."""
        dir_text = "vượt lên trên" if direction == "up" else "giảm xuống dưới"
        return (
            f"🚨 <b>CẢNH BÁO GIÁ</b>\n\n"
            f"<b>{symbol}</b> đã {dir_text} ngưỡng!\n"
            f"💰 Giá hiện tại: <b>{current_price:,.0f}đ</b>\n"
            f"🎯 Ngưỡng đặt: {target_price:,.0f}đ"
        )

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

        # New strong recommendations
        recs = data.get("new_recommendations", [])
        if recs:
            lines.append("💡 <b>Khuyến nghị mới:</b>")
            for r in recs[:5]:
                emoji = MessageFormatter._recommendation_emoji(r.get("signal", ""))
                lines.append(
                    f"  {emoji} <b>{r['symbol']}</b>: {r.get('signal', '—')} ({r.get('score', '—')}/10)"
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
