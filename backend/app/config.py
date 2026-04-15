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


settings = Settings()
