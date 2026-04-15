from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Database
    database_url: str  # postgresql+asyncpg://...

    # Crawling
    vnstock_source: str = "VCI"
    crawl_batch_size: int = 50
    crawl_delay_seconds: float = 2.0
    crawl_max_retries: int = 3
    backfill_start_date: str = "2023-07-01"

    # Scheduler
    daily_crawl_hour: int = 15
    daily_crawl_minute: int = 30
    timezone: str = "Asia/Ho_Chi_Minh"

    # Gemini AI (Phase 2)
    gemini_api_key: str = ""  # Required — get from https://aistudio.google.com/apikey
    gemini_model: str = "gemini-2.0-flash"
    gemini_batch_size: int = 10  # Tickers per Gemini prompt (per CONTEXT.md: 5-10)
    gemini_delay_seconds: float = 4.0  # Min 4s for 15 RPM free tier (per RESEARCH.md pitfall 2)
    gemini_max_retries: int = 3

    # Indicator computation (Phase 2)
    indicator_compute_days: int = 60  # Compute for most recent N days per run

    # CafeF News Scraping (Phase 3)
    cafef_delay_seconds: float = 1.0  # Delay between requests per CONTEXT.md
    cafef_news_days: int = 7  # Scrape news from last N days per CONTEXT.md

    # Telegram Bot (Phase 4)
    telegram_bot_token: str = ""  # Required for bot — get from @BotFather on Telegram
    telegram_chat_id: str = ""  # Your personal chat ID — get from @userinfobot


settings = Settings()
