import ssl
import urllib3
import httpx

# Suppress SSL warnings for crawler connections (self-signed proxy certs)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Create a no-verify SSL context for crawlers only (not for DB or Gemini)
CRAWLER_SSL_CONTEXT = ssl.create_default_context()
CRAWLER_SSL_CONTEXT.check_hostname = False
CRAWLER_SSL_CONTEXT.verify_mode = ssl.CERT_NONE

# Patch httpx AsyncClient to disable SSL only for crawler HTTP calls.
# DB (asyncpg) and Gemini SDK use their own connections — unaffected.
if not getattr(httpx.AsyncClient.__init__, '_holo_patched', False):
    _original_httpx_client_init = httpx.AsyncClient.__init__
    def _patched_httpx_client_init(self, *args, **kwargs):
        kwargs.setdefault("verify", False)
        _original_httpx_client_init(self, *args, **kwargs)
    _patched_httpx_client_init._holo_patched = True
    httpx.AsyncClient.__init__ = _patched_httpx_client_init

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Database
    database_url: str  # postgresql+asyncpg://...

    # Crawling
    vnstock_source: str = "VCI"
    crawl_batch_size: int = 50
    crawl_delay_seconds: float = 3.5  # vnstock free tier: 20 req/min
    crawl_max_retries: int = 3
    backfill_start_date: str = "2023-07-01"

    # Scheduler
    daily_crawl_hour: int = 15
    daily_crawl_minute: int = 30
    timezone: str = "Asia/Ho_Chi_Minh"

    # Gemini AI (Phase 2)
    gemini_api_key: str = ""  # Required — get from https://aistudio.google.com/apikey
    gemini_model: str = "gemini-3.1-flash-lite-preview"
    gemini_batch_size: int = 8  # Reduced from 15 — more tokens per ticker for detailed analysis
    rumor_batch_size: int = 6  # Tickers per Gemini call for rumor scoring (30 tickers / 6 = 5 calls)
    gemini_delay_seconds: float = 4.0  # Delay between batches for rate-limit safety
    gemini_max_retries: int = 3

    # Indicator computation (Phase 2)
    indicator_compute_days: int = 60  # Compute for most recent N days per run

    # CafeF News Scraping (Phase 3)
    cafef_delay_seconds: float = 1.0  # Delay between requests per CONTEXT.md
    cafef_news_days: int = 7  # Scrape news from last N days per CONTEXT.md

    # Fireant Community Crawling (Phase 60)
    fireant_token: str = ""  # Guest JWT from Fireant.vn — get from __NEXT_DATA__
    fireant_delay_seconds: float = 1.5  # Between ticker requests
    fireant_post_limit: int = 20  # Posts per ticker per crawl
    fireant_retention_days: int = 30  # Delete posts older than N days

    # Circuit Breaker (Phase 6)
    circuit_breaker_fail_max: int = 3
    circuit_breaker_reset_timeout: float = 120.0  # 2 minutes cooldown

    # External API Timeouts (Phase 6)
    vnstock_timeout: float = 30.0
    gemini_timeout: float = 60.0

    # VNDirect Corporate Events (Phase 7)
    vndirect_delay_seconds: float = 1.0  # Delay between ticker requests
    vndirect_timeout: float = 15.0

    # Real-time WebSocket (Phase 16)
    realtime_poll_interval: int = 30  # seconds between VCI price polls
    realtime_max_symbols: int = 50  # max symbols per poll request
    realtime_priority_exchanges: list[str] = ["HOSE", "HNX", "UPCOM"]  # exchange priority for symbol selection

    # VNDirect WebSocket (Phase 76) — domain decommissioned, disabled
    vndirect_ws_url: str = "wss://price-cmc-04.vndirect.com.vn/realtime/websocket"
    vndirect_ws_enabled: bool = False  # Domain no longer resolves; use VCI polling instead

    # Telegram Channel Monitor (Phase 83)
    telegram_api_id: int = 0
    telegram_api_hash: str = ""
    telegram_session_string: str = ""
    telegram_channels: list[str] = []
    telegram_fetch_limit: int = 50
    telegram_delay_seconds: float = 1.5
    telegram_enabled: bool = False

    # Trading Signal Pipeline (Phase 19)
    trading_signal_batch_size: int = 8     # Reduced from 15 — more tokens per ticker
    trading_signal_thinking_budget: int = 2048  # Doubled from 1024 — complex dual-direction reasoning
    trading_signal_max_tokens: int = 32768     # Doubled from 16384 — ~300 tokens/ticker × 15 tickers

    # Combined Analysis (Phase 51 — structured sections need more tokens)
    combined_thinking_budget: int = 2048   # Match trading_signal — complex multi-dimensional reasoning
    combined_max_tokens: int = 32768       # Match trading_signal — 4 structured sections per ticker

    # Unified Analysis Pipeline (Phase 88 / v19.0)
    unified_batch_size: int = 6            # Fewer tickers per batch — more data per ticker
    unified_thinking_budget: int = 2048    # Complex multi-dimensional reasoning
    unified_max_tokens: int = 32768        # ~500 tokens/ticker × 6 tickers + overhead

    # Test Mode (Phase 27 — E2E testing)
    holo_test_mode: bool = False  # Set True to skip scheduler in tests

    # CORS — additional allowed origins (comma-separated URLs)
    cors_origins: str = ""


settings = Settings()
