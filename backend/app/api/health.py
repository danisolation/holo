"""Health monitoring API endpoints.

Provides system health visibility: job statuses, data freshness,
error rates, DB pool stats, manual job triggers, and Gemini API usage.
Per D-10-01: New router at /health prefix.
"""
from fastapi import APIRouter, HTTPException, Query
from loguru import logger

from app.database import async_session, engine
from app.scheduler.manager import scheduler
from app.services.health_service import HealthService
from app.schemas.health import (
    JobStatusResponse, DataFreshnessResponse, ErrorRateResponse,
    DbPoolResponse, TriggerResponse, GeminiUsageResponse, GeminiUsageToday,
    GeminiUsageTodayBreakdown, GeminiUsageDaily,
)

router = APIRouter(prefix="/health", tags=["health"])

JOB_TRIGGER_MAP: dict[str, tuple[str, str]] = {
    "crawl": ("daily_price_crawl_manual", "daily_price_crawl"),
    "indicators": ("daily_indicator_compute_manual", "daily_indicator_compute"),
    "ai": ("daily_ai_analysis_manual", "daily_ai_analysis"),
    "news": ("daily_news_crawl_manual", "daily_news_crawl"),
    "sentiment": ("daily_sentiment_manual", "daily_sentiment_analysis"),
    "combined": ("daily_combined_manual", "daily_combined_analysis"),
}


@router.get("/jobs", response_model=JobStatusResponse)
async def get_job_statuses():
    """Latest execution status per job with color coding."""
    async with async_session() as session:
        svc = HealthService(session)
        jobs = await svc.get_job_statuses()
        return JobStatusResponse(jobs=jobs)


@router.get("/data-freshness", response_model=DataFreshnessResponse)
async def get_data_freshness():
    """Last update timestamps per data type with stale flags."""
    async with async_session() as session:
        svc = HealthService(session)
        items = await svc.get_data_freshness()
        return DataFreshnessResponse(items=items)


@router.get("/errors", response_model=ErrorRateResponse)
async def get_error_rates():
    """Error rate per job over the last 7 days."""
    async with async_session() as session:
        svc = HealthService(session)
        jobs = await svc.get_error_rates(days=7)
        return ErrorRateResponse(jobs=jobs)


@router.get("/db-pool", response_model=DbPoolResponse)
async def get_db_pool_status():
    """Database connection pool statistics."""
    pool = engine.pool
    return DbPoolResponse(
        pool_size=pool.size(),
        checked_in=pool.checkedin(),
        checked_out=pool.checkedout(),
        overflow=pool.overflow(),
        max_overflow=3,
    )


@router.post("/trigger/{job_name}", response_model=TriggerResponse)
async def trigger_job(job_name: str):
    """Manually trigger a pipeline job. Per D-10-04."""
    if job_name not in JOB_TRIGGER_MAP:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown job: '{job_name}'. Valid: {', '.join(sorted(JOB_TRIGGER_MAP.keys()))}"
        )
    manual_id, func_name = JOB_TRIGGER_MAP[job_name]

    from app.scheduler import jobs as job_module
    job_func = getattr(job_module, func_name)

    scheduler.add_job(
        job_func,
        id=manual_id,
        replace_existing=True,
        misfire_grace_time=3600,
    )
    logger.info(f"Manual trigger: {job_name} → {manual_id}")
    return TriggerResponse(message=f"Job '{job_name}' triggered", triggered=True)


@router.get("/summary")
async def get_health_summary():
    """Overall health summary aggregating jobs + freshness + pool."""
    async with async_session() as session:
        svc = HealthService(session)
        jobs = await svc.get_job_statuses()
        freshness = await svc.get_data_freshness()

    pool = engine.pool
    job_colors = [j["color"] for j in jobs]
    stale_count = sum(1 for f in freshness if f["is_stale"])

    if "red" in job_colors or stale_count > 0:
        overall = "degraded"
    elif "yellow" in job_colors:
        overall = "warning"
    else:
        overall = "healthy"

    return {
        "status": overall,
        "jobs_total": len(jobs),
        "jobs_healthy": job_colors.count("green"),
        "jobs_warning": job_colors.count("yellow"),
        "jobs_error": job_colors.count("red"),
        "data_sources_total": len(freshness),
        "data_sources_stale": stale_count,
        "pool_checked_out": pool.checkedout(),
        "pool_available": pool.size() - pool.checkedout() + (3 - pool.overflow()),
    }


# Gemini free-tier limits (D-15-02)
GEMINI_FREE_TIER_RPD = 1500       # Requests per day
GEMINI_FREE_TIER_TOKENS = 1_000_000  # Tokens per day


@router.get("/gemini-usage", response_model=GeminiUsageResponse)
async def get_gemini_usage(days: int = Query(default=7, ge=1)):
    """Gemini API usage: today's progress vs limits + daily history.

    Per D-15-09: Aggregated usage data for the health dashboard.
    """
    # Cap days at 30 to prevent excessive queries
    days = min(days, 30)

    from app.services.gemini_usage_service import GeminiUsageService

    async with async_session() as session:
        svc = GeminiUsageService(session)
        today_data = await svc.get_today_usage()
        daily_data = await svc.get_daily_usage(days=days)

    today = GeminiUsageToday(
        requests=today_data["requests"],
        tokens=today_data["tokens"],
        limit_requests=GEMINI_FREE_TIER_RPD,
        limit_tokens=GEMINI_FREE_TIER_TOKENS,
        breakdown=[
            GeminiUsageTodayBreakdown(**item)
            for item in today_data["breakdown"]
        ],
    )
    daily = [GeminiUsageDaily(**item) for item in daily_data]

    return GeminiUsageResponse(today=today, daily=daily)
