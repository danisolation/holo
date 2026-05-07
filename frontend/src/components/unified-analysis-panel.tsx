"use client";

import {
  TrendingUp,
  TrendingDown,
  Minus,
  Target,
  ShieldAlert,
  Trophy,
  Layers,
  Clock,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import type { UnifiedAnalysisData } from "@/lib/api";

function SignalBadge({ signal, score }: { signal: string; score: number }) {
  const normalized = signal.toLowerCase().replace("á", "a").replace("ữ", "u");
  let variant: "default" | "destructive" | "secondary" = "secondary";
  let icon = <Minus className="size-3.5" />;
  let label = "Giữ";

  if (normalized.includes("mua") || normalized === "buy") {
    variant = "default";
    icon = <TrendingUp className="size-3.5" />;
    label = "MUA";
  } else if (normalized.includes("ban") || normalized === "sell") {
    variant = "destructive";
    icon = <TrendingDown className="size-3.5" />;
    label = "BÁN";
  }

  return (
    <div className="flex items-center gap-2">
      <Badge variant={variant} className="gap-1 text-sm px-3 py-1">
        {icon}
        {label}
      </Badge>
      <span className="text-2xl font-bold font-mono">{score}/10</span>
    </div>
  );
}

function PriceLevel({
  label,
  value,
  icon,
  color,
}: {
  label: string;
  value: number | undefined;
  icon: React.ReactNode;
  color: string;
}) {
  if (!value) return null;
  return (
    <div className="flex items-center gap-2">
      <span className={color}>{icon}</span>
      <span className="text-sm text-muted-foreground">{label}</span>
      <span className="ml-auto font-mono font-medium text-sm">
        {value.toLocaleString("vi-VN")} đ
      </span>
    </div>
  );
}

interface UnifiedAnalysisPanelProps {
  data: UnifiedAnalysisData;
  symbol: string;
}

export function UnifiedAnalysisPanel({ data, symbol }: UnifiedAnalysisPanelProps) {
  return (
    <Card className="border-2">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg">Phân tích tổng hợp AI</CardTitle>
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <Clock className="size-3" />
            {data.analysis_date}
          </div>
        </div>
        <SignalBadge signal={data.signal} score={data.score} />
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Trading Plan */}
        {(data.entry_price || data.stop_loss || data.take_profit_1) && (
          <div className="rounded-lg bg-muted/50 p-3 space-y-2">
            <h4 className="text-sm font-semibold flex items-center gap-1.5">
              <Target className="size-4 text-primary" />
              Kế hoạch giao dịch
            </h4>
            <div className="space-y-1.5">
              <PriceLevel
                label="Entry"
                value={data.entry_price}
                icon={<Target className="size-3.5" />}
                color="text-blue-500"
              />
              <PriceLevel
                label="Stop Loss"
                value={data.stop_loss}
                icon={<ShieldAlert className="size-3.5" />}
                color="text-red-500"
              />
              <PriceLevel
                label="Take Profit 1"
                value={data.take_profit_1}
                icon={<Trophy className="size-3.5" />}
                color="text-green-500"
              />
              <PriceLevel
                label="Take Profit 2"
                value={data.take_profit_2}
                icon={<Trophy className="size-3.5" />}
                color="text-emerald-600"
              />
            </div>
            {(data.risk_reward_ratio || data.position_size_pct || data.timeframe) && (
              <div className="flex flex-wrap gap-3 pt-2 border-t text-xs text-muted-foreground">
                {data.risk_reward_ratio && (
                  <span>R:R {data.risk_reward_ratio.toFixed(1)}</span>
                )}
                {data.position_size_pct && (
                  <span>Size {data.position_size_pct}%</span>
                )}
                {data.timeframe && <span>{data.timeframe}</span>}
              </div>
            )}
          </div>
        )}

        {/* Key Levels */}
        {data.key_levels && (
          <div className="rounded-lg bg-muted/50 p-3">
            <h4 className="text-sm font-semibold flex items-center gap-1.5 mb-1">
              <Layers className="size-4 text-primary" />
              Mức giá quan trọng
            </h4>
            <p className="text-sm text-muted-foreground">{data.key_levels}</p>
          </div>
        )}

        {/* Reasoning */}
        <div>
          <h4 className="text-sm font-semibold mb-1">Phân tích chi tiết</h4>
          <p className="text-sm text-muted-foreground whitespace-pre-line leading-relaxed">
            {data.reasoning}
          </p>
        </div>
      </CardContent>
    </Card>
  );
}
