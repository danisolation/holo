"use client";

import { useState } from "react";
import {
  Brain,
  ChevronDown,
  ChevronUp,
  TrendingUp,
  TrendingDown,
  Minus,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useSectorAnalysis } from "@/lib/hooks";
import type { SectorStrengthItem } from "@/lib/api";

const strengthConfig = {
  strong: {
    label: "Mạnh",
    className: "bg-emerald-500/20 text-emerald-400",
  },
  neutral: {
    label: "Trung tính",
    className: "bg-zinc-500/20 text-zinc-400",
  },
  weak: {
    label: "Yếu",
    className: "bg-red-500/20 text-red-400",
  },
} as const;

const trendConfig = {
  improving: { icon: TrendingUp, label: "↑", className: "text-emerald-400" },
  stable: { icon: Minus, label: "→", className: "text-zinc-400" },
  declining: { icon: TrendingDown, label: "↓", className: "text-red-400" },
} as const;

const flowConfig = {
  inflow: { label: "Vào", className: "text-emerald-400" },
  neutral: { label: "Cân bằng", className: "text-zinc-400" },
  outflow: { label: "Ra", className: "text-red-400" },
} as const;

function SectorRow({ sector }: { sector: SectorStrengthItem }) {
  const strength = strengthConfig[sector.strength] ?? strengthConfig.neutral;
  const trend = trendConfig[sector.trend] ?? trendConfig.stable;
  const flow = flowConfig[sector.money_flow] ?? flowConfig.neutral;

  return (
    <div className="py-2 px-2 rounded-md hover:bg-muted/50 transition-colors">
      <div className="flex items-center justify-between mb-1">
        <span className="font-medium text-sm">{sector.sector}</span>
        <div className="flex items-center gap-2">
          <span
            className={`text-xs font-medium px-1.5 py-0.5 rounded ${strength.className}`}
          >
            {strength.label}
          </span>
          <span className={`text-xs font-medium ${trend.className}`}>
            {trend.label}
          </span>
          <span className={`text-xs ${flow.className}`}>{flow.label}</span>
        </div>
      </div>
      <p className="text-xs text-muted-foreground leading-relaxed">
        {sector.reasoning}
      </p>
    </div>
  );
}

export function SectorAIPanel() {
  const { data, isLoading, error } = useSectorAnalysis();
  const [expanded, setExpanded] = useState(false);

  // Don't block page on error
  if (error) return null;

  if (isLoading) {
    return (
      <Card className="mt-6">
        <CardHeader>
          <Skeleton className="h-6 w-48" />
        </CardHeader>
        <CardContent className="space-y-3">
          <Skeleton className="h-4 w-full" />
          <Skeleton className="h-4 w-3/4" />
          <Skeleton className="h-4 w-2/3" />
        </CardContent>
      </Card>
    );
  }

  if (!data) {
    return (
      <Card className="mt-6">
        <CardContent className="flex items-center justify-center py-6">
          <p className="text-sm text-muted-foreground">
            Chưa có phân tích ngành
          </p>
        </CardContent>
      </Card>
    );
  }

  const { analysis, analysis_date } = data;

  return (
    <Card className="mt-6">
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2 text-violet-500">
            <Brain className="size-4" />
            Phân tích ngành AI
          </CardTitle>
          <span className="text-xs text-muted-foreground">{analysis_date}</span>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Market sentiment */}
        <p className="text-sm leading-relaxed">{analysis.market_sentiment}</p>

        {/* Top strong / weak */}
        <div className="grid grid-cols-2 gap-3">
          <div>
            <h4 className="text-xs font-semibold text-emerald-400 mb-1.5">
              Ngành mạnh
            </h4>
            <div className="flex flex-wrap gap-1">
              {analysis.top_strong.map((name) => (
                <span
                  key={name}
                  className="text-xs px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-400"
                >
                  {name}
                </span>
              ))}
            </div>
          </div>
          <div>
            <h4 className="text-xs font-semibold text-red-400 mb-1.5">
              Ngành yếu
            </h4>
            <div className="flex flex-wrap gap-1">
              {analysis.top_weak.map((name) => (
                <span
                  key={name}
                  className="text-xs px-2 py-0.5 rounded bg-red-500/20 text-red-400"
                >
                  {name}
                </span>
              ))}
            </div>
          </div>
        </div>

        {/* Rotation recommendation */}
        <div className="rounded-[min(var(--radius-md),12px)] bg-muted/50 p-3">
          <h4 className="text-xs font-semibold mb-1">Gợi ý rotation</h4>
          <p className="text-xs text-muted-foreground leading-relaxed">
            {analysis.rotation.recommendation}
          </p>
        </div>

        {/* Expandable sector details */}
        <button
          onClick={() => setExpanded(!expanded)}
          className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors w-full justify-center py-1"
        >
          {expanded ? (
            <>
              Thu gọn <ChevronUp className="size-3" />
            </>
          ) : (
            <>
              Chi tiết {analysis.sectors.length} ngành{" "}
              <ChevronDown className="size-3" />
            </>
          )}
        </button>

        {expanded && (
          <div className="space-y-1 max-h-[400px] overflow-y-auto">
            {analysis.sectors.map((sector) => (
              <SectorRow key={sector.sector} sector={sector} />
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
