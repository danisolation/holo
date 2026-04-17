import os
import ssl
import urllib3
import httpx
import requests

# Disable SSL verification globally (corporate proxy with self-signed cert)
os.environ["PYTHONHTTPSVERIFY"] = "0"
os.environ["CURL_CA_BUNDLE"] = ""
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Patch ssl.SSLContext.wrap_socket — the only reliable way to disable
# SSL verification across all libraries (requests, httpx, urllib3, asyncpg)
_orig_ssl_wrap = ssl.SSLContext.wrap_socket
def _patched_ssl_wrap(self, *args, **kwargs):
    self.check_hostname = False
    self.verify_mode = ssl.CERT_NONE
    return _orig_ssl_wrap(self, *args, **kwargs)
ssl.SSLContext.wrap_socket = _patched_ssl_wrap

# Also patch httpx async client (uses its own SSL handling)
_original_httpx_client_init = httpx.AsyncClient.__init__
def _patched_httpx_client_init(self, *args, **kwargs):
    kwargs.setdefault("verify", False)
    _original_httpx_client_init(self, *args, **kwargs)
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
    gemini_model: str = "gemini-2.5-flash-lite"
    gemini_batch_size: int = 25  # 25/batch = 16 batches for 400 tickers
    gemini_delay_seconds: float = 4.0  # Delay between batches for rate-limit safety
    gemini_max_retries: int = 3

    # Indicator computation (Phase 2)
    indicator_compute_days: int = 60  # Compute for most recent N days per run

    # CafeF News Scraping (Phase 3)
    cafef_delay_seconds: float = 1.0  # Delay between requests per CONTEXT.md
    cafef_news_days: int = 7  # Scrape news from last N days per CONTEXT.md

    # Telegram Bot (Phase 4)
    telegram_bot_token: str = ""  # Required for bot — get from @BotFather on Telegram
    telegram_chat_id: str = ""  # Your personal chat ID — get from @userinfobot

    # Circuit Breaker (Phase 6)
    circuit_breaker_fail_max: int = 3
    circuit_breaker_reset_timeout: float = 120.0  # 2 minutes cooldown

    # External API Timeouts (Phase 6)
    vnstock_timeout: float = 30.0
    gemini_timeout: float = 60.0


settings = Settings()
