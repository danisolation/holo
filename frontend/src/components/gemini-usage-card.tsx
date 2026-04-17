"use client";

import { useGeminiUsage } from "@/lib/hooks";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Bot } from "lucide-react";
import { AreaChart, Area, ResponsiveContainer } from "recharts";

function formatTokens(value: number): string {
  if (value >= 1_000_000) return `${(value / 1_000_000).toFixed(1)}M`;
  if (value >= 1_000) return `${Math.round(value / 1_000)}K`;
  return String(value);
}

function formatNumber(value: number): string {
  return new Intl.NumberFormat("vi-VN").format(value);
}

function getProgressColor(value: number, max: number): string {
  const pct = max > 0 ? (value / max) * 100 : 0;
  if (pct > 90) return "bg-red-500";
  if (pct >= 75) return "bg-yellow-500";
  return "bg-primary";
}

function getProgressPct(value: number, max: number): number {
  if (max <= 0) return 0;
  return Math.min((value / max) * 100, 100);
}

const ANALYSIS_LABELS: Record<string, string> = {
  technical: "Technical",
  fundamental: "Fundamental",
  sentiment: "Sentiment",
  combined: "Combined",
};

export function GeminiUsageCard() {
  const { data, isLoading, error } = useGeminiUsage(7);

  if (isLoading) return <Skeleton className="h-48" />;
  if (error || !data) {
    return (
      <p className="text-xs text-muted-foreground">
        Không thể tải Gemini usage.
      </p>
    );
  }

  const { today, daily } = data;
  const reqPct = getProgressPct(today.requests, today.limit_requests);
  const tokenPct = getProgressPct(today.tokens, today.limit_tokens);
  const reqColor = getProgressColor(today.requests, today.limit_requests);
  const tokenColor = getProgressColor(today.tokens, today.limit_tokens);

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm font-semibold flex items-center gap-2">
          <Bot className="size-4" />
          Gemini API Usage (Hôm nay)
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Progress bars */}
        <div className="space-y-3">
          {/* Requests */}
          <div className="space-y-1">
            <div className="flex items-center justify-between">
              <span className="text-sm">Requests</span>
              <span className="text-xs text-muted-foreground">
                {formatNumber(today.requests)} / {formatNumber(today.limit_requests)}
              </span>
            </div>
            <div className="h-2 rounded-full bg-muted overflow-hidden">
              <div
                className={`h-full rounded-full ${reqColor}`}
                style={{ width: `${reqPct}%` }}
                role="progressbar"
                aria-valuenow={today.requests}
                aria-valuemin={0}
                aria-valuemax={today.limit_requests}
              />
            </div>
          </div>

          {/* Tokens */}
          <div className="space-y-1">
            <div className="flex items-center justify-between">
              <span className="text-sm">Tokens</span>
              <span className="text-xs text-muted-foreground">
                {formatTokens(today.tokens)} / {formatTokens(today.limit_tokens)}
              </span>
            </div>
            <div className="h-2 rounded-full bg-muted overflow-hidden">
              <div
                className={`h-full rounded-full ${tokenColor}`}
                style={{ width: `${tokenPct}%` }}
                role="progressbar"
                aria-valuenow={today.tokens}
                aria-valuemin={0}
                aria-valuemax={today.limit_tokens}
              />
            </div>
          </div>
        </div>

        {/* Breakdown grid */}
        {today.breakdown.length > 0 && (
          <div>
            <p className="text-xs text-muted-foreground mb-2">Breakdown (requests):</p>
            <div className="grid grid-cols-2 gap-x-4 gap-y-1">
              {today.breakdown.map((item) => (
                <div key={item.analysis_type} className="flex items-center justify-between text-xs">
                  <span>{ANALYSIS_LABELS[item.analysis_type] ?? item.analysis_type}</span>
                  <span className="text-muted-foreground">{item.requests}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* 7-day trend mini chart */}
        {daily.length > 0 && (
          <div>
            <p className="text-xs text-muted-foreground mb-1">7-day trend:</p>
            <ResponsiveContainer width="100%" height={48}>
              <AreaChart data={daily}>
                <defs>
                  <linearGradient id="geminiTrendGradient" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="hsl(var(--primary))" stopOpacity={0.3} />
                    <stop offset="100%" stopColor="hsl(var(--primary))" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <Area
                  type="monotone"
                  dataKey="tokens"
                  stroke="hsl(var(--primary))"
                  strokeWidth={1.5}
                  fill="url(#geminiTrendGradient)"
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
