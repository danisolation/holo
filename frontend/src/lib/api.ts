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

export async function fetchTickers(sector?: string, exchange?: string): Promise<Ticker[]> {
  const params = new URLSearchParams();
  if (sector) params.set("sector", sector);
  if (exchange && exchange !== "all") params.set("exchange", exchange);
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
): Promise<IndicatorData[]> {
  return apiFetch<IndicatorData[]>(
    `/analysis/${encodeURIComponent(symbol)}/indicators?limit=${limit}`,
  );
}

export async function fetchAnalysisSummary(
  symbol: string,
): Promise<AnalysisSummary> {
  return apiFetch<AnalysisSummary>(
    `/analysis/${encodeURIComponent(symbol)}/summary`,
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

export async function fetchMarketOverview(exchange?: string): Promise<MarketTicker[]> {
  const params = exchange && exchange !== "all" ? `?exchange=${encodeURIComponent(exchange)}` : "";
  return apiFetch<MarketTicker[]>(`/tickers/market-overview${params}`);
}

export async function triggerOnDemandAnalysis(symbol: string): Promise<{ message: string; triggered: boolean }> {
  return apiFetch<{ message: string; triggered: boolean }>(
    `/analysis/${encodeURIComponent(symbol)}/analyze-now`,
    { method: "POST" },
  );
}

// --- Portfolio Types ---

export interface TradeRequest {
  symbol: string;
  side: "BUY" | "SELL";
  quantity: number;
  price: number;
  trade_date: string;
  fees?: number;
}

export interface TradeResponse {
  id: number;
  symbol: string;
  side: string;
  quantity: number;
  price: number;
  fees: number;
  trade_date: string;
  created_at: string;
  realized_pnl: number | null;
}

export interface HoldingResponse {
  symbol: string;
  name: string;
  quantity: number;
  avg_cost: number;
  market_price: number | null;
  market_value: number | null;
  total_cost: number;
  unrealized_pnl: number | null;
  unrealized_pnl_pct: number | null;
  dividend_income: number;
  sector: string | null;
}

export interface PortfolioSummaryResponse {
  total_invested: number;
  total_market_value: number | null;
  total_realized_pnl: number;
  total_unrealized_pnl: number | null;
  total_return_pct: number | null;
  holdings_count: number;
  dividend_income: number;
}

export interface TradeHistoryResponse {
  trades: TradeResponse[];
  total: number;
}

// --- Portfolio Enhancement Types (Phase 13) ---

export interface PerformanceDataPoint {
  date: string;
  value: number;
}

export interface PerformanceResponse {
  data: PerformanceDataPoint[];
  period: string;
}

export interface AllocationItem {
  name: string;
  value: number;
  percentage: number;
}

export interface AllocationResponse {
  data: AllocationItem[];
  mode: string;
  total_value: number;
}

export interface TradeUpdateRequest {
  side: "BUY" | "SELL";
  quantity: number;
  price: number;
  trade_date: string;
  fees?: number;
}

export interface CSVPreviewRow {
  row_number: number;
  symbol: string;
  side: string;
  quantity: number;
  price: number;
  trade_date: string;
  fees: number;
  status: "valid" | "warning" | "error";
  message: string | null;
}

export interface CSVDryRunResponse {
  format_detected: string;
  rows: CSVPreviewRow[];
  total_valid: number;
  total_warnings: number;
  total_errors: number;
}

export interface CSVImportResponse {
  trades_imported: number;
  tickers_recalculated: number;
}

// --- Portfolio Fetch Functions ---

export async function fetchHoldings(): Promise<HoldingResponse[]> {
  return apiFetch<HoldingResponse[]>("/portfolio/holdings");
}

export async function fetchPortfolioSummary(): Promise<PortfolioSummaryResponse> {
  return apiFetch<PortfolioSummaryResponse>("/portfolio/summary");
}

export async function fetchTradeHistory(params?: {
  ticker?: string;
  side?: string;
  limit?: number;
  offset?: number;
}): Promise<TradeHistoryResponse> {
  const searchParams = new URLSearchParams();
  if (params?.ticker) searchParams.set("ticker", params.ticker);
  if (params?.side) searchParams.set("side", params.side);
  if (params?.limit) searchParams.set("limit", String(params.limit));
  if (params?.offset) searchParams.set("offset", String(params.offset));
  const qs = searchParams.toString();
  return apiFetch<TradeHistoryResponse>(`/portfolio/trades${qs ? `?${qs}` : ""}`);
}

export async function createTrade(trade: TradeRequest): Promise<TradeResponse> {
  return apiFetch<TradeResponse>("/portfolio/trades", {
    method: "POST",
    body: JSON.stringify(trade),
  });
}

// --- Portfolio Enhancement Fetch Functions (Phase 13) ---

export async function fetchPerformanceData(period: string = "3M"): Promise<PerformanceResponse> {
  return apiFetch<PerformanceResponse>(`/portfolio/performance?period=${encodeURIComponent(period)}`);
}

export async function fetchAllocationData(mode: string = "ticker"): Promise<AllocationResponse> {
  return apiFetch<AllocationResponse>(`/portfolio/allocation?mode=${encodeURIComponent(mode)}`);
}

export async function updateTrade(tradeId: number, data: TradeUpdateRequest): Promise<TradeResponse> {
  return apiFetch<TradeResponse>(`/portfolio/trades/${tradeId}`, {
    method: "PUT",
    body: JSON.stringify(data),
  });
}

export async function deleteTrade(tradeId: number): Promise<{ deleted: boolean; trade_id: number }> {
  return apiFetch<{ deleted: boolean; trade_id: number }>(`/portfolio/trades/${tradeId}`, {
    method: "DELETE",
  });
}

export async function uploadCSVDryRun(file: File): Promise<CSVDryRunResponse> {
  const formData = new FormData();
  formData.append("file", file);
  const url = `${API_BASE}/portfolio/import?dry_run=true`;
  const res = await fetch(url, { method: "POST", body: formData });
  if (!res.ok) {
    const body = await res.text().catch(() => "Unknown error");
    throw new ApiError(res.status, `${res.status}: ${body}`);
  }
  return res.json();
}

export async function importCSV(file: File): Promise<CSVImportResponse> {
  const formData = new FormData();
  formData.append("file", file);
  const url = `${API_BASE}/portfolio/import?dry_run=false`;
  const res = await fetch(url, { method: "POST", body: formData });
  if (!res.ok) {
    const body = await res.text().catch(() => "Unknown error");
    throw new ApiError(res.status, `${res.status}: ${body}`);
  }
  return res.json();
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

// --- Paper Trading Types (Phase 25) ---

export interface PaperTradeResponse {
  id: number;
  symbol: string;
  direction: "long" | "bearish";
  status: string;
  entry_price: number;
  stop_loss: number;
  take_profit_1: number;
  take_profit_2: number;
  adjusted_stop_loss: number | null;
  quantity: number;
  closed_quantity: number;
  realized_pnl: number | null;
  realized_pnl_pct: number | null;
  exit_price: number | null;
  partial_exit_price: number | null;
  signal_date: string;
  entry_date: string | null;
  closed_date: string | null;
  confidence: number;
  timeframe: string;
  position_size_pct: number;
  risk_reward_ratio: number;
  created_at: string;
}

export interface PaperTradeListResponse {
  trades: PaperTradeResponse[];
  total: number;
}

export interface SimulationConfigResponse {
  initial_capital: number;
  auto_track_enabled: boolean;
  min_confidence_threshold: number;
}

export interface SimulationConfigUpdateRequest {
  initial_capital?: number;
  auto_track_enabled?: boolean;
  min_confidence_threshold?: number;
}

export interface AnalyticsSummaryResponse {
  total_trades: number;
  wins: number;
  losses: number;
  win_rate: number;
  total_pnl: number;
  total_pnl_pct: number;
  avg_pnl_per_trade: number;
}

// --- Paper Trading Fetch Functions (Phase 25) ---

export async function fetchPaperTrades(params?: {
  status?: string;
  direction?: string;
  timeframe?: string;
  symbol?: string;
  limit?: number;
  offset?: number;
}): Promise<PaperTradeListResponse> {
  const searchParams = new URLSearchParams();
  if (params?.status) searchParams.set("status", params.status);
  if (params?.direction) searchParams.set("direction", params.direction);
  if (params?.timeframe) searchParams.set("timeframe", params.timeframe);
  if (params?.symbol) searchParams.set("symbol", params.symbol);
  if (params?.limit) searchParams.set("limit", String(params.limit));
  if (params?.offset) searchParams.set("offset", String(params.offset));
  const qs = searchParams.toString();
  return apiFetch<PaperTradeListResponse>(`/paper-trading/trades${qs ? `?${qs}` : ""}`);
}

export async function closePaperTrade(tradeId: number): Promise<PaperTradeResponse> {
  return apiFetch<PaperTradeResponse>(`/paper-trading/trades/${tradeId}/close`, { method: "POST" });
}

export async function fetchPaperConfig(): Promise<SimulationConfigResponse> {
  return apiFetch<SimulationConfigResponse>("/paper-trading/config");
}

export async function updatePaperConfig(data: SimulationConfigUpdateRequest): Promise<SimulationConfigResponse> {
  return apiFetch<SimulationConfigResponse>("/paper-trading/config", {
    method: "PUT",
    body: JSON.stringify(data),
  });
}

export async function fetchPaperAnalyticsSummary(): Promise<AnalyticsSummaryResponse> {
  return apiFetch<AnalyticsSummaryResponse>("/paper-trading/analytics/summary");
}

export interface ManualFollowRequest {
  symbol: string;
  direction: "long" | "bearish";
  entry_price: number;
  stop_loss: number;
  take_profit_1: number;
  take_profit_2: number;
  timeframe: "swing" | "position";
  confidence: number;
  position_size_pct: number;
}

export async function createManualFollow(data: ManualFollowRequest): Promise<PaperTradeResponse> {
  return apiFetch<PaperTradeResponse>("/paper-trading/trades/follow", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

// --- Paper Trading Analytics Types (Phase 26) ---

export interface EquityCurvePoint {
  date: string;
  daily_pnl: number;
  cumulative_pnl: number;
}

export interface EquityCurveResponse {
  data: EquityCurvePoint[];
  initial_capital: number;
}

export interface DrawdownPeriod {
  start: string;
  end: string | null;
  drawdown_vnd: number;
}

export interface DrawdownResponse {
  max_drawdown_vnd: number;
  max_drawdown_pct: number;
  current_drawdown_vnd: number;
  current_drawdown_pct: number;
  periods: DrawdownPeriod[];
}

export interface DirectionAnalysisItem {
  direction: string;
  total_trades: number;
  wins: number;
  losses: number;
  win_rate: number;
  total_pnl: number;
  avg_pnl: number;
}

export interface ConfidenceBracketItem {
  bracket: string;
  total_trades: number;
  wins: number;
  win_rate: number;
  avg_pnl: number;
  avg_pnl_pct: number;
}

export interface RiskRewardResponse {
  avg_predicted_rr: number;
  avg_achieved_rr: number;
  trades_above_predicted: number;
  trades_below_predicted: number;
  total_trades: number;
}

export interface ProfitFactorResponse {
  gross_profit: number;
  gross_loss: number;
  profit_factor: number | null;
  expected_value: number;
  total_trades: number;
}

export interface SectorAnalysisItem {
  sector: string;
  total_trades: number;
  wins: number;
  win_rate: number;
  total_pnl: number;
  avg_pnl: number;
}

// New Phase 26 endpoints
export interface StreakResponse {
  current_win_streak: number;
  current_loss_streak: number;
  longest_win_streak: number;
  longest_loss_streak: number;
  total_trades: number;
}

export interface TimeframeComparisonItem {
  timeframe: string;
  total_trades: number;
  wins: number;
  losses: number;
  win_rate: number;
  total_pnl: number;
  avg_pnl: number;
}

export interface PeriodicSummaryItem {
  period: string;
  total_trades: number;
  wins: number;
  losses: number;
  win_rate: number;
  total_pnl: number;
  avg_rr: number;
}

export interface CalendarDataPoint {
  date: string;
  daily_pnl: number;
  trade_count: number;
}

// --- Paper Trading Analytics Fetch Functions (Phase 26) ---

// Existing Phase 24 endpoints (types added above)
export async function fetchPaperEquityCurve(): Promise<EquityCurveResponse> {
  return apiFetch<EquityCurveResponse>("/paper-trading/analytics/equity-curve");
}
export async function fetchPaperDrawdown(): Promise<DrawdownResponse> {
  return apiFetch<DrawdownResponse>("/paper-trading/analytics/drawdown");
}
export async function fetchPaperDirection(): Promise<DirectionAnalysisItem[]> {
  return apiFetch<DirectionAnalysisItem[]>("/paper-trading/analytics/direction");
}
export async function fetchPaperConfidence(): Promise<ConfidenceBracketItem[]> {
  return apiFetch<ConfidenceBracketItem[]>("/paper-trading/analytics/confidence");
}
export async function fetchPaperRiskReward(): Promise<RiskRewardResponse> {
  return apiFetch<RiskRewardResponse>("/paper-trading/analytics/risk-reward");
}
export async function fetchPaperProfitFactor(): Promise<ProfitFactorResponse> {
  return apiFetch<ProfitFactorResponse>("/paper-trading/analytics/profit-factor");
}
export async function fetchPaperSector(): Promise<SectorAnalysisItem[]> {
  return apiFetch<SectorAnalysisItem[]>("/paper-trading/analytics/sector");
}

// New Phase 26 endpoints
export async function fetchPaperStreaks(): Promise<StreakResponse> {
  return apiFetch<StreakResponse>("/paper-trading/analytics/streaks");
}
export async function fetchPaperTimeframe(): Promise<TimeframeComparisonItem[]> {
  return apiFetch<TimeframeComparisonItem[]>("/paper-trading/analytics/timeframe");
}
export async function fetchPaperPeriodic(period: "weekly" | "monthly" = "weekly"): Promise<PeriodicSummaryItem[]> {
  return apiFetch<PeriodicSummaryItem[]>(`/paper-trading/analytics/periodic?period=${period}`);
}
export async function fetchPaperCalendar(): Promise<CalendarDataPoint[]> {
  return apiFetch<CalendarDataPoint[]>("/paper-trading/analytics/calendar");
}
