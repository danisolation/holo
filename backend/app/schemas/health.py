"""Pydantic schemas for health monitoring API endpoints."""
from pydantic import BaseModel


class JobStatusItem(BaseModel):
    """Single job's latest execution status."""
    job_id: str
    job_name: str
    status: str
    color: str
    started_at: str | None
    completed_at: str | None
    duration_seconds: float | None
    result_summary: dict | None
    error_message: str | None


class JobStatusResponse(BaseModel):
    """GET /health/jobs response."""
    jobs: list[JobStatusItem]


class DataFreshnessItem(BaseModel):
    """Single data source freshness."""
    data_type: str
    table_name: str
    latest: str | None
    is_stale: bool
    threshold_hours: int


class DataFreshnessResponse(BaseModel):
    """GET /health/data-freshness response."""
    items: list[DataFreshnessItem]


class ErrorRateDayItem(BaseModel):
    """Error count for a single day."""
    day: str
    total: int
    failed: int


class ErrorRateJobItem(BaseModel):
    """Error rate for a single job over 7 days."""
    job_id: str
    job_name: str
    days: list[ErrorRateDayItem]
    total_runs: int
    total_failures: int


class ErrorRateResponse(BaseModel):
    """GET /health/errors response."""
    jobs: list[ErrorRateJobItem]


class DbPoolResponse(BaseModel):
    """GET /health/db-pool response."""
    pool_size: int
    checked_in: int
    checked_out: int
    overflow: int
    max_overflow: int


class TriggerResponse(BaseModel):
    """POST /health/trigger/{job_name} response."""
    message: str
    triggered: bool


# ---- Gemini Usage Schemas (D-15-09) ----

class GeminiUsageTodayBreakdown(BaseModel):
    """Per-analysis-type usage breakdown for today."""
    analysis_type: str
    requests: int
    tokens: int


class GeminiUsageToday(BaseModel):
    """Today's Gemini usage vs free-tier limits."""
    requests: int
    tokens: int
    limit_requests: int  # 1500 RPD
    limit_tokens: int    # 1,000,000 tokens/day
    breakdown: list[GeminiUsageTodayBreakdown]


class GeminiUsageDaily(BaseModel):
    """Single day's aggregated Gemini usage."""
    date: str
    tokens: int
    requests: int


class GeminiUsageResponse(BaseModel):
    """GET /health/gemini-usage response."""
    today: GeminiUsageToday
    daily: list[GeminiUsageDaily]
