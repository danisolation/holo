const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";

// --- Types matching backend Pydantic schemas ---

export interface Ticker {
  symbol: string;
  name: string;
  sector: string | null;
  industry: string | null;
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

export async function fetchTickers(sector?: string): Promise<Ticker[]> {
  const params = sector ? `?sector=${encodeURIComponent(sector)}` : "";
  return apiFetch<Ticker[]>(`/tickers/${params}`);
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

// --- Market Overview (heatmap data) ---

export interface MarketTicker {
  symbol: string;
  name: string;
  sector: string | null;
  market_cap: number | null;
  last_price: number | null;
  change_pct: number | null;
}

export async function fetchMarketOverview(): Promise<MarketTicker[]> {
  return apiFetch<MarketTicker[]>("/tickers/market-overview");
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
}

export interface PortfolioSummaryResponse {
  total_invested: number;
  total_market_value: number | null;
  total_realized_pnl: number;
  total_unrealized_pnl: number | null;
  total_return_pct: number | null;
  holdings_count: number;
}

export interface TradeHistoryResponse {
  trades: TradeResponse[];
  total: number;
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
