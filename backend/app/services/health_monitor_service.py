"""Health self-ping and Telegram alerting service.

Periodically pings /api/health and sends Telegram alerts when the service
goes down or comes back up. Tracks response times for uptime reporting.
"""
import asyncio
import time
import logging
from datetime import datetime, timezone

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

# In-memory state
_last_status: bool | None = None  # None = unknown, True = up, False = down
_ping_history: list[dict] = []  # Recent ping results (max 1000)
MAX_HISTORY = 1000


async def send_telegram_alert(message: str) -> None:
    """Send alert via Telegram Bot API."""
    token = settings.telegram_bot_token
    chat_id = settings.telegram_alert_chat_id
    if not token or not chat_id:
        logger.debug("Telegram alert skipped — no bot token or chat ID configured")
        return

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "HTML",
    }
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(url, json=payload)
            if resp.status_code != 200:
                logger.warning(f"Telegram alert failed: {resp.status_code} {resp.text[:200]}")
    except Exception as e:
        logger.error(f"Telegram alert error: {e}")


async def ping_health() -> dict:
    """Ping own /api/health endpoint and return result."""
    global _last_status

    start = time.monotonic()
    result = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "status": "unknown",
        "response_time_ms": 0,
        "status_code": 0,
    }

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get("http://127.0.0.1:8000/api/health")
            elapsed_ms = round((time.monotonic() - start) * 1000)
            result["response_time_ms"] = elapsed_ms
            result["status_code"] = resp.status_code

            if resp.status_code == 200:
                result["status"] = "up"
                if _last_status is False:
                    await send_telegram_alert(
                        f"✅ <b>Holo UP</b>\n"
                        f"Service recovered — response {elapsed_ms}ms\n"
                        f"Time: {result['timestamp']}"
                    )
                _last_status = True
            else:
                result["status"] = "degraded"
                if _last_status is not False:
                    await send_telegram_alert(
                        f"⚠️ <b>Holo DEGRADED</b>\n"
                        f"Health check returned {resp.status_code}\n"
                        f"Time: {result['timestamp']}"
                    )
                _last_status = False

    except Exception as e:
        elapsed_ms = round((time.monotonic() - start) * 1000)
        result["response_time_ms"] = elapsed_ms
        result["status"] = "down"
        if _last_status is not False:
            await send_telegram_alert(
                f"🔴 <b>Holo DOWN</b>\n"
                f"Health check failed: {str(e)[:100]}\n"
                f"Time: {result['timestamp']}"
            )
        _last_status = False

    _ping_history.append(result)
    if len(_ping_history) > MAX_HISTORY:
        _ping_history.pop(0)

    return result


def get_uptime_stats() -> dict:
    """Calculate uptime stats from ping history."""
    if not _ping_history:
        return {
            "total_pings": 0,
            "uptime_pct": 0.0,
            "avg_response_ms": 0,
            "last_status": "unknown",
            "recent_pings": [],
        }

    up_count = sum(1 for p in _ping_history if p["status"] == "up")
    total = len(_ping_history)
    up_times = [p["response_time_ms"] for p in _ping_history if p["status"] == "up"]
    avg_ms = round(sum(up_times) / len(up_times)) if up_times else 0

    return {
        "total_pings": total,
        "uptime_pct": round(up_count / total * 100, 2),
        "avg_response_ms": avg_ms,
        "last_status": _ping_history[-1]["status"],
        "recent_pings": _ping_history[-20:],
    }
