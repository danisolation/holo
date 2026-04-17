"use client";

import { useRouter } from "next/navigation";
import type { MarketTicker } from "@/lib/api";
import { ExchangeBadge } from "@/components/exchange-badge";

/**
 * Interpolate change_pct to a color between red ↔ gray ↔ green.
 * Range: -5% = deep red, 0% = neutral gray, +5% = deep green
 */
function getChangeColor(pct: number | null): string {
  if (pct == null) return "rgba(100, 100, 100, 0.4)";

  const clamped = Math.max(-5, Math.min(5, pct));
  const t = (clamped + 5) / 10; // 0..1 where 0.5 is neutral

  if (t < 0.5) {
    // Red side: interpolate from deep red to gray
    const ratio = t / 0.5; // 0..1
    const r = Math.round(239 - (239 - 80) * ratio);
    const g = Math.round(83 + (80 - 83) * ratio);
    const b = Math.round(80 + (80 - 80) * ratio);
    return `rgb(${r}, ${g}, ${b})`;
  } else {
    // Green side: interpolate from gray to deep green
    const ratio = (t - 0.5) / 0.5; // 0..1
    const r = Math.round(80 - (80 - 38) * ratio);
    const g = Math.round(80 + (166 - 80) * ratio);
    const b = Math.round(80 + (154 - 80) * ratio);
    return `rgb(${r}, ${g}, ${b})`;
  }
}

interface HeatmapProps {
  data: MarketTicker[];
  exchange?: string;
}

const EXCHANGE_BORDER_COLORS: Record<string, string> = {
  HOSE: "border-[var(--exchange-hose)]",
  HNX: "border-[var(--exchange-hnx)]",
  UPCOM: "border-[var(--exchange-upcom)]",
};

export function Heatmap({ data, exchange }: HeatmapProps) {
  const router = useRouter();

  // Group tickers by sector
  const grouped = data.reduce<Record<string, MarketTicker[]>>((acc, ticker) => {
    const sector = ticker.sector ?? "Khác";
    if (!acc[sector]) acc[sector] = [];
    acc[sector].push(ticker);
    return acc;
  }, {});

  // Sort sectors by ticker count (largest first)
  const sectors = Object.entries(grouped).sort(
    ([, a], [, b]) => b.length - a.length
  );

  if (data.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-64 text-muted-foreground">
        <p className="font-medium">Không có dữ liệu</p>
        {exchange && exchange !== "all" && (
          <p className="text-sm mt-1">
            Không có mã nào trên sàn {exchange} hoặc dữ liệu chưa được cập nhật.
          </p>
        )}
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {sectors.map(([sector, tickers]) => (
        <div key={sector}>
          <h3 className="text-sm font-medium text-muted-foreground mb-2 px-1">
            {sector}{" "}
            <span className="text-xs">({tickers.length})</span>
          </h3>

          {/* Mobile: scrollable list view */}
          <div className="md:hidden overflow-y-auto max-h-[60vh] space-y-0.5">
            {tickers.map((ticker) => (
              <button
                key={ticker.symbol}
                onClick={() => router.push(`/ticker/${ticker.symbol}`)}
                className="w-full flex items-center justify-between px-3 py-2 rounded-md hover:bg-muted/50 transition-colors cursor-pointer"
                style={{
                  borderLeft: `3px solid ${getChangeColor(ticker.change_pct)}`,
                }}
              >
                <div className="flex items-center gap-2">
                  <span className="font-mono font-bold text-sm w-14 text-left">
                    {ticker.symbol}
                  </span>
                  <ExchangeBadge exchange={ticker.exchange} />
                  <span className="text-xs text-muted-foreground truncate max-w-[140px]">
                    {ticker.name}
                  </span>
                </div>
                <span
                  className={`font-mono text-sm ${
                    ticker.change_pct != null && ticker.change_pct > 0
                      ? "text-[#26a69a]"
                      : ticker.change_pct != null && ticker.change_pct < 0
                        ? "text-[#ef5350]"
                        : "text-muted-foreground"
                  }`}
                >
                  {ticker.change_pct != null
                    ? (ticker.change_pct >= 0 ? "+" : "") +
                      ticker.change_pct.toFixed(2) +
                      "%"
                    : "—"}
                </span>
              </button>
            ))}
          </div>

          {/* Desktop: dense grid heatmap */}
          <div className="hidden md:grid grid-cols-8 lg:grid-cols-10 xl:grid-cols-12 gap-1">
            {tickers.map((ticker) => (
              <button
                key={ticker.symbol}
                onClick={() => router.push(`/ticker/${ticker.symbol}`)}
                className={`relative flex flex-col items-center justify-center rounded-md px-1 py-2 text-white transition-transform hover:scale-105 hover:z-10 hover:ring-1 hover:ring-white/30 cursor-pointer min-h-[52px] border-2 ${EXCHANGE_BORDER_COLORS[ticker.exchange] ?? ""}`}
                style={{ backgroundColor: getChangeColor(ticker.change_pct) }}
                title={`${ticker.name} — ${ticker.change_pct != null ? (ticker.change_pct >= 0 ? "+" : "") + ticker.change_pct.toFixed(2) + "%" : "N/A"}`}
              >
                <span className="text-[11px] font-bold leading-tight truncate w-full text-center">
                  {ticker.symbol}
                </span>
                <span className="text-[10px] leading-tight opacity-90">
                  {ticker.change_pct != null
                    ? (ticker.change_pct >= 0 ? "+" : "") +
                      ticker.change_pct.toFixed(2) +
                      "%"
                    : "—"}
                </span>
              </button>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}
