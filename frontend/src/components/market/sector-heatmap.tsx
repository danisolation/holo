"use client";

import { useState } from "react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import type { SectorPerformanceItem } from "@/lib/api";

/**
 * Interpolate change_pct to a color between red ↔ gray ↔ green.
 * Range: -5% = deep red, 0% = neutral gray, +5% = deep green
 */
function getChangeColor(pct: number | null): string {
  if (pct == null) return "rgba(100, 100, 100, 0.4)";

  const clamped = Math.max(-5, Math.min(5, pct));
  const t = (clamped + 5) / 10; // 0..1 where 0.5 is neutral

  if (t < 0.5) {
    const ratio = t / 0.5;
    const r = Math.round(239 - (239 - 80) * ratio);
    const g = Math.round(83 + (80 - 83) * ratio);
    const b = Math.round(80 + (80 - 80) * ratio);
    return `rgb(${r}, ${g}, ${b})`;
  } else {
    const ratio = (t - 0.5) / 0.5;
    const r = Math.round(80 - (80 - 38) * ratio);
    const g = Math.round(80 + (166 - 80) * ratio);
    const b = Math.round(80 + (154 - 80) * ratio);
    return `rgb(${r}, ${g}, ${b})`;
  }
}

/** Get a blue-shade color based on ticker count (for volume view). */
function getVolumeColor(tickerCount: number, maxCount: number): string {
  const ratio = Math.min(tickerCount / Math.max(maxCount, 1), 1);
  const base = 40;
  const r = Math.round(base + (1 - ratio) * 60);
  const g = Math.round(base + 80 + (1 - ratio) * 40);
  const b = Math.round(150 + ratio * 105);
  return `rgb(${r}, ${g}, ${b})`;
}

/** Calculate grid column span proportional to ticker_count. */
function getColSpan(tickerCount: number, maxCount: number): number {
  if (maxCount <= 0) return 1;
  const ratio = tickerCount / maxCount;
  if (ratio > 0.6) return 3;
  if (ratio > 0.3) return 2;
  return 1;
}

interface SectorHeatmapProps {
  sectors: SectorPerformanceItem[];
}

export function SectorHeatmap({ sectors }: SectorHeatmapProps) {
  const [viewMode, setViewMode] = useState<"price" | "volume">("price");

  const maxTickerCount = Math.max(...sectors.map((s) => s.ticker_count), 1);

  // Sort sectors by ticker_count desc for layout
  const sorted = [...sectors].sort((a, b) => b.ticker_count - a.ticker_count);

  return (
    <div className="space-y-4">
      {/* Toggle buttons */}
      <div className="flex items-center gap-2">
        <span className="text-sm text-muted-foreground mr-1">Hiển thị:</span>
        <Button
          variant={viewMode === "price" ? "default" : "outline"}
          size="sm"
          onClick={() => setViewMode("price")}
        >
          % Giá
        </Button>
        <Button
          variant={viewMode === "volume" ? "default" : "outline"}
          size="sm"
          onClick={() => setViewMode("volume")}
        >
          Khối lượng
        </Button>
      </div>

      {/* Heatmap grid */}
      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 lg:grid-cols-6 gap-1.5">
        {sorted.map((sector) => {
          const bgColor =
            viewMode === "price"
              ? getChangeColor(sector.avg_change_today)
              : getVolumeColor(sector.ticker_count, maxTickerCount);

          const colSpan = getColSpan(sector.ticker_count, maxTickerCount);

          const displayValue =
            viewMode === "price"
              ? sector.avg_change_today != null
                ? `${sector.avg_change_today >= 0 ? "+" : ""}${sector.avg_change_today.toFixed(2)}%`
                : "—"
              : `${sector.ticker_count} mã`;

          return (
            <Link
              key={sector.sector}
              href={`/market/sector/${encodeURIComponent(sector.sector)}`}
              className="relative flex flex-col items-center justify-center rounded-md px-2 py-3 text-white transition-transform hover:scale-[1.03] hover:z-10 hover:ring-1 hover:ring-white/30 cursor-pointer min-h-[72px]"
              style={{
                backgroundColor: bgColor,
                gridColumn: `span ${Math.min(colSpan, 2)}`,
              }}
              title={`${sector.sector}: ${sector.ticker_count} mã, today: ${sector.avg_change_today?.toFixed(2) ?? "N/A"}%`}
            >
              <span className="text-xs font-bold leading-tight text-center line-clamp-2">
                {sector.sector}
              </span>
              <span className="text-[11px] leading-tight opacity-90 mt-0.5">
                {displayValue}
              </span>
              <span className="text-[10px] leading-tight opacity-60 mt-0.5">
                {sector.ticker_count} mã
              </span>
            </Link>
          );
        })}
      </div>
    </div>
  );
}
