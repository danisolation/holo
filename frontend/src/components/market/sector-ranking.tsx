"use client";

import { useState } from "react";
import type { SectorPerformanceItem } from "@/lib/api";

type SortKey = "today" | "7d" | "30d";

function getSortValue(
  sector: SectorPerformanceItem,
  key: SortKey
): number {
  switch (key) {
    case "today":
      return sector.avg_change_today ?? -Infinity;
    case "7d":
      return sector.avg_change_7d ?? -Infinity;
    case "30d":
      return sector.avg_change_30d ?? -Infinity;
  }
}

function formatPct(value: number | null): string {
  if (value == null) return "—";
  return `${value >= 0 ? "+" : ""}${value.toFixed(2)}%`;
}

function pctColorClass(value: number | null): string {
  if (value == null) return "text-muted-foreground";
  if (value > 0) return "text-trading-bull";
  if (value < 0) return "text-trading-bear";
  return "text-muted-foreground";
}

/** Trend arrow: compare 7d vs 30d momentum */
function getTrend(sector: SectorPerformanceItem): {
  arrow: string;
  color: string;
} {
  const d7 = sector.avg_change_7d ?? 0;
  const d30 = sector.avg_change_30d ?? 0;
  if (d7 > d30) return { arrow: "▲", color: "text-trading-bull" };
  if (d7 < d30) return { arrow: "▼", color: "text-trading-bear" };
  return { arrow: "—", color: "text-muted-foreground" };
}

interface SectorRankingProps {
  sectors: SectorPerformanceItem[];
}

export function SectorRanking({ sectors }: SectorRankingProps) {
  const [sortBy, setSortBy] = useState<SortKey>("today");

  const sorted = [...sectors].sort(
    (a, b) => getSortValue(b, sortBy) - getSortValue(a, sortBy)
  );

  const headerBtn = (label: string, key: SortKey) => (
    <button
      onClick={() => setSortBy(key)}
      className={`font-medium text-right cursor-pointer hover:text-foreground transition-colors ${
        sortBy === key ? "text-foreground underline" : "text-muted-foreground"
      }`}
    >
      {label}
    </button>
  );

  return (
    <div>
      <h3 className="text-sm font-semibold mb-3">Xếp hạng ngành</h3>
      <div className="overflow-x-auto -mx-4 px-4 md:mx-0 md:px-0">
        <table className="w-full text-sm min-w-[520px]">
          <thead>
            <tr className="border-b text-left">
              <th className="py-2 pr-3 font-medium text-muted-foreground">
                Ngành
              </th>
              <th className="py-2 pr-3 font-medium text-muted-foreground text-right">
                Mã
              </th>
              <th className="py-2 pr-3 text-right">
                {headerBtn("Hôm nay", "today")}
              </th>
              <th className="py-2 pr-3 text-right hidden sm:table-cell">
                {headerBtn("7 ngày", "7d")}
              </th>
              <th className="py-2 pr-3 text-right hidden sm:table-cell">
                {headerBtn("30 ngày", "30d")}
              </th>
              <th className="py-2 font-medium text-muted-foreground text-center hidden md:table-cell">
                Xu hướng
              </th>
            </tr>
          </thead>
          <tbody>
            {sorted.map((sector) => {
              const trend = getTrend(sector);
              return (
                <tr
                  key={sector.sector}
                  className="border-b last:border-0 hover:bg-muted/50"
                >
                  <td className="py-2 pr-3 font-medium truncate max-w-[200px]">
                    {sector.sector}
                  </td>
                  <td className="py-2 pr-3 text-right font-mono text-muted-foreground">
                    {sector.ticker_count}
                  </td>
                  <td
                    className={`py-2 pr-3 text-right font-mono ${pctColorClass(sector.avg_change_today)}`}
                  >
                    {formatPct(sector.avg_change_today)}
                  </td>
                  <td
                    className={`py-2 pr-3 text-right font-mono hidden sm:table-cell ${pctColorClass(sector.avg_change_7d)}`}
                  >
                    {formatPct(sector.avg_change_7d)}
                  </td>
                  <td
                    className={`py-2 pr-3 text-right font-mono hidden sm:table-cell ${pctColorClass(sector.avg_change_30d)}`}
                  >
                    {formatPct(sector.avg_change_30d)}
                  </td>
                  <td
                    className={`py-2 text-center font-bold hidden md:table-cell ${trend.color}`}
                  >
                    {trend.arrow}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
