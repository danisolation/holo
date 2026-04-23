const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";

// --- Types matching backend Pydantic schemas ---

export interface Ticker {
  symbol: string;
  name: string;
  sector: string | null;
  industry: string | null;
  exchange: string;
  market_cap: number | null;
  is_active: boolean;
}

export interface PriceData {
  date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface IndicatorData {
  ticker_symbol: string;
  date: string;
  rsi_14: number | null;
  macd_line: number | null;
  macd_signal: number | null;
  macd_histogram: number | null;
  sma_20: number | null;
  sma_50: number | null;
  sma_200: number | null;
  ema_12: number | null;
  ema_26: number | null;
  bb_upper: number | null;
  bb_middle: number | null;
  bb_lower: number | null;
  // Phase 17: Volatility, Trend Strength, Momentum
  atr_14: number | null;
  adx_14: number | null;
  plus_di_14: number | null;
  minus_di_14: number | null;
  stoch_k_14: number | null;
  stoch_d_14: number | null;
  // Phase 18: Support & Resistance Levels
  pivot_point: number | null;
  support_1: number | null;
  support_2: number | null;
  resistance_1: number | null;
  resistance_2: number | null;
  fib_236: number | null;
  fib_382: number | null;
  fib_500: number | null;
  fib_618: number | null;
}

export interface AnalysisResult {
  ticker_symbol: string;
  analysis_type: string;
  analysis_date: string;
  signal: string;
  score: number;
  reasoning: string;
  model_version: string;
}

export interface AnalysisSummary {
  ticker_symbol: string;
  technical?: AnalysisResult;
  fundamental?: AnalysisResult;
  sentiment?: AnalysisResult;
  combined?: AnalysisResult;
  trading_signal?: AnalysisResult;  // Phase 20
}

export interface NewsArticleResponse {
  title: string;
  url: string;
  published_at: string;
}

// --- Phase 20: Trading Plan Types ---

export interface TradingPlanDetail {
  entry_price: number;
  stop_loss: number;
  take_profit_1: number;
  take_profit_2: number;
  risk_reward_ratio: number;
  position_size_pct: number;
  timeframe: "swing" | "position";
}

export interface DirectionAnalysis {
  direction: "long" | "bearish";
  confidence: number;           // 1-10
  trading_plan: TradingPlanDetail;
  reasoning: string;            // Vietnamese text
}

export interface TickerTradingSignal {
  ticker: string;
  recommended_direction: "long" | "bearish";
  long_analysis: DirectionAnalysis;
  bearish_analysis: DirectionAnalysis;
}

// --- Phase 43: Daily Picks Types ---

export interface DailyPickResponse {
  pick_date: string;
  ticker_symbol: string;
  ticker_name: string;
  rank: number | null;
  composite_score: number;
  entry_price: number | null;
  stop_loss: number | null;
  take_profit_1: number | null;
  take_profit_2: number | null;
  risk_reward: number | null;
  position_size_shares: number | null;
  position_size_vnd: number | null;
  position_size_pct: number | null;
  explanation: string | null;
  status: "picked" | "almost";
  rejection_reason: string | null;
}

export interface DailyPicksResponse {
  date: string;
  capital: number;
  picks: DailyPickResponse[];
  almost_selected: DailyPickResponse[];
}

export interface ProfileResponse {
  capital: number;
  risk_level: number;
  broker_fee_pct: number;
}

export interface ProfileUpdate {
  capital: number;
  risk_level: number;
}

// --- API Error ---

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const url = `${API_BASE}${path}`;
  const res = await fetch(url, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...init?.headers,
    },
  });

  if (!res.ok) {
    const body = await res.text().catch(() => "Unknown error");
    throw new ApiError(res.status, `${res.status} ${res.statusText}: ${body}`);
  }

  return res.json() as Promise<T>;
}

// --- Fetch Functions ---

export async function fetchTickers(
  sector?: string,
  exchange?: string,
  limit?: number,
  offset?: number,
): Promise<Ticker[]> {
  const params = new URLSearchParams();
  if (sector) params.set("sector", sector);
  if (exchange && exchange !== "all") params.set("exchange", exchange);
  if (limit !== undefined) params.set("limit", String(limit));
  if (offset !== undefined) params.set("offset", String(offset));
  const qs = params.toString();
  return apiFetch<Ticker[]>(`/tickers/${qs ? `?${qs}` : ""}`);
}

export async function fetchPrices(
  symbol: string,
  days: number = 365,
): Promise<PriceData[]> {
  return apiFetch<PriceData[]>(
    `/tickers/${encodeURIComponent(symbol)}/prices?days=${days}`,
  );
}

export async function fetchIndicators(
  symbol: string,
  limit: number = 100,
  offset: number = 0,
): Promise<IndicatorData[]> {
  const params = new URLSearchParams({ limit: String(limit) });
  if (offset > 0) params.set("offset", String(offset));
  return apiFetch<IndicatorData[]>(
    `/analysis/${encodeURIComponent(symbol)}/indicators?${params}`,
  );
}

export async function fetchAnalysisSummary(
  symbol: string,
): Promise<AnalysisSummary> {
  return apiFetch<AnalysisSummary>(
    `/analysis/${encodeURIComponent(symbol)}/summary`,
  );
}

export async function fetchTickerNews(
  symbol: string,
  limit: number = 10,
  offset: number = 0,
): Promise<NewsArticleResponse[]> {
  const params = new URLSearchParams({ limit: String(limit) });
  if (offset > 0) params.set("offset", String(offset));
  return apiFetch<NewsArticleResponse[]>(
    `/analysis/${encodeURIComponent(symbol)}/news?${params}`,
  );
}

export async function fetchTradingSignal(
  symbol: string,
): Promise<TickerTradingSignal | null> {
  try {
    const result = await apiFetch<
      AnalysisResult & { raw_response?: TickerTradingSignal }
    >(`/analysis/${encodeURIComponent(symbol)}/trading-signal`);
    return result.raw_response ?? null;
  } catch (e) {
    if (e instanceof ApiError && e.status === 404) return null;
    throw e;
  }
}

// --- Market Overview (heatmap data) ---

export interface MarketTicker {
  symbol: string;
  name: string;
  sector: string | null;
  exchange: string;
  market_cap: number | null;
  last_price: number | null;
  change_pct: number | null;
}

export interface MarketOverviewParams {
  exchange?: string;
  sort?: "change_pct" | "market_cap" | "symbol";
  order?: "desc" | "asc";
  top?: number;
}

export async function fetchMarketOverview(params?: MarketOverviewParams): Promise<MarketTicker[]> {
  const searchParams = new URLSearchParams();
  if (params?.exchange && params.exchange !== "all") {
    searchParams.set("exchange", params.exchange);
  }
  if (params?.sort) searchParams.set("sort", params.sort);
  if (params?.order) searchParams.set("order", params.order);
  if (params?.top) searchParams.set("top", String(params.top));
  const qs = searchParams.toString();
  return apiFetch<MarketTicker[]>(`/tickers/market-overview${qs ? `?${qs}` : ""}`);
}

export async function triggerOnDemandAnalysis(symbol: string): Promise<{ message: string; triggered: boolean }> {
  return apiFetch<{ message: string; triggered: boolean }>(
    `/analysis/${encodeURIComponent(symbol)}/analyze-now`,
    { method: "POST" },
  );
}

// --- Health Types ---

export interface JobStatusItem {
  job_id: string;
  job_name: string;
  status: string;
  color: "green" | "yellow" | "red";
  started_at: string | null;
  completed_at: string | null;
  duration_seconds: number | null;
  result_summary: Record<string, unknown> | null;
  error_message: string | null;
}

export interface JobStatusResponse {
  jobs: JobStatusItem[];
}

export interface DataFreshnessItem {
  data_type: string;
  table_name: string;
  latest: string | null;
  is_stale: boolean;
  threshold_hours: number;
}

export interface DataFreshnessResponse {
  items: DataFreshnessItem[];
}

export interface ErrorRateDayItem {
  day: string;
  total: number;
  failed: number;
}

export interface ErrorRateJobItem {
  job_id: string;
  job_name: string;
  days: ErrorRateDayItem[];
  total_runs: number;
  total_failures: number;
}

export interface ErrorRateResponse {
  jobs: ErrorRateJobItem[];
}

export interface DbPoolResponse {
  pool_size: number;
  checked_in: number;
  checked_out: number;
  overflow: number;
  max_overflow: number;
}

export interface TriggerResponse {
  message: string;
  triggered: boolean;
}

export interface HealthSummary {
  status: "healthy" | "warning" | "degraded";
  jobs_total: number;
  jobs_healthy: number;
  jobs_warning: number;
  jobs_error: number;
  data_sources_total: number;
  data_sources_stale: number;
  pool_checked_out: number;
  pool_available: number;
}

// --- Health Fetch Functions ---

export async function fetchJobStatuses(): Promise<JobStatusResponse> {
  return apiFetch<JobStatusResponse>("/health/jobs");
}

export async function fetchDataFreshness(): Promise<DataFreshnessResponse> {
  return apiFetch<DataFreshnessResponse>("/health/data-freshness");
}

export async function fetchErrorRates(): Promise<ErrorRateResponse> {
  return apiFetch<ErrorRateResponse>("/health/errors");
}

export async function fetchDbPool(): Promise<DbPoolResponse> {
  return apiFetch<DbPoolResponse>("/health/db-pool");
}

export async function fetchHealthSummary(): Promise<HealthSummary> {
  return apiFetch<HealthSummary>("/health/summary");
}

export async function triggerJob(jobName: string): Promise<TriggerResponse> {
  return apiFetch<TriggerResponse>(
    `/health/trigger/${encodeURIComponent(jobName)}`,
    { method: "POST" }
  );
}

// --- Corporate Events Types (Phase 14) ---

export interface CorporateEventResponse {
  id: number;
  symbol: string;
  name: string;
  event_type: string;
  ex_date: string;
  record_date: string | null;
  announcement_date: string | null;
  dividend_amount: number | null;
  ratio: number | null;
  note: string | null;
}

export async function fetchCorporateEvents(params?: {
  month?: string;
  type?: string;
  symbol?: string;
}): Promise<CorporateEventResponse[]> {
  const searchParams = new URLSearchParams();
  if (params?.month) searchParams.set("month", params.month);
  if (params?.type) searchParams.set("type", params.type);
  if (params?.symbol) searchParams.set("symbol", params.symbol);
  const qs = searchParams.toString();
  return apiFetch<CorporateEventResponse[]>(`/corporate-events/${qs ? `?${qs}` : ""}`);
}

// --- Gemini Usage Types (Phase 15) ---

export interface GeminiUsageTodayBreakdown {
  analysis_type: string;
  requests: number;
  tokens: number;
}

export interface GeminiUsageToday {
  requests: number;
  tokens: number;
  limit_requests: number;
  limit_tokens: number;
  breakdown: GeminiUsageTodayBreakdown[];
}

export interface GeminiUsageDaily {
  date: string;
  tokens: number;
  requests: number;
}

export interface GeminiUsageResponse {
  today: GeminiUsageToday;
  daily: GeminiUsageDaily[];
}

// --- Pipeline Timeline Types (Phase 15) ---

export interface PipelineStep {
  job_id: string;
  job_name: string;
  started_at: string;
  duration_seconds: number | null;
  status: string;
}

export interface PipelineRun {
  date: string;
  total_seconds: number;
  steps: PipelineStep[];
}

export interface PipelineTimelineResponse {
  runs: PipelineRun[];
}

// --- Gemini Usage & Pipeline Timeline Fetch Functions (Phase 15) ---

export async function fetchGeminiUsage(days: number = 7): Promise<GeminiUsageResponse> {
  return apiFetch<GeminiUsageResponse>(`/health/gemini-usage?days=${days}`);
}

export async function fetchPipelineTimeline(days: number = 7): Promise<PipelineTimelineResponse> {
  return apiFetch<PipelineTimelineResponse>(`/health/pipeline-timeline?days=${days}`);
}

// --- Phase 43: Daily Picks API ---

export async function fetchDailyPicks(): Promise<DailyPicksResponse> {
  return apiFetch<DailyPicksResponse>("/picks/today");
}

export async function fetchPickHistory(days: number = 30): Promise<DailyPickResponse[]> {
  return apiFetch<DailyPickResponse[]>(`/picks/history?days=${days}`);
}

export async function fetchProfile(): Promise<ProfileResponse> {
  return apiFetch<ProfileResponse>("/profile");
}

export async function updateProfile(data: ProfileUpdate): Promise<ProfileResponse> {
  return apiFetch<ProfileResponse>("/profile", {
    method: "PUT",
    body: JSON.stringify(data),
  });
}
