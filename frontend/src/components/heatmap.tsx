"use client";

import { useRouter } from "next/navigation";
import type { MarketTicker } from "@/lib/api";

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
}

export function Heatmap({ data }: HeatmapProps) {
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
      <div className="flex items-center justify-center h-64 text-muted-foreground">
        Không có dữ liệu thị trường
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
          <div className="grid grid-cols-4 sm:grid-cols-6 md:grid-cols-8 lg:grid-cols-10 xl:grid-cols-12 gap-1">
            {tickers.map((ticker) => (
              <button
                key={ticker.symbol}
                onClick={() => router.push(`/ticker/${ticker.symbol}`)}
                className="relative flex flex-col items-center justify-center rounded-md px-1 py-2 text-white transition-transform hover:scale-105 hover:z-10 hover:ring-1 hover:ring-white/30 cursor-pointer min-h-[52px]"
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
