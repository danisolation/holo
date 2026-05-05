"use client";

import { Target, TrendingUp, TrendingDown, Minus } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { useAccuracyStats } from "@/lib/hooks";

const DIRECTION_LABELS: Record<string, { label: string; icon: typeof TrendingUp }> = {
  mua: { label: "Mua", icon: TrendingUp },
  ban: { label: "Bán", icon: TrendingDown },
  giu: { label: "Giữ", icon: Minus },
};

function AccuracyBadge({ pct }: { pct: number }) {
  const variant = pct >= 60 ? "default" : pct >= 40 ? "secondary" : "destructive";
  return <Badge variant={variant}>{pct.toFixed(1)}%</Badge>;
}

export function AccuracyCard() {
  const { data, isLoading, isError } = useAccuracyStats(30);

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <Target className="size-4" />
            Độ chính xác AI
          </CardTitle>
        </CardHeader>
        <CardContent>
          <Skeleton className="h-20 w-full" />
        </CardContent>
      </Card>
    );
  }

  if (isError || !data) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <Target className="size-4" />
            Độ chính xác AI
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">Không tải được dữ liệu.</p>
        </CardContent>
      </Card>
    );
  }

  if (data.total === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <Target className="size-4" />
            Độ chính xác AI
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            Chưa có đủ dữ liệu. Hệ thống sẽ bắt đầu theo dõi sau 7 ngày phân tích đầu tiên.
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <Target className="size-4" />
          Độ chính xác AI (30 ngày)
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Overall accuracy */}
        <div className="flex items-center justify-between">
          <span className="text-sm font-medium">Tổng thể</span>
          <div className="flex items-center gap-2">
            <span className="text-2xl font-bold">{data.overall_accuracy_pct.toFixed(1)}%</span>
            <span className="text-xs text-muted-foreground">
              ({data.correct}/{data.total} dự đoán)
            </span>
          </div>
        </div>

        {/* Per-direction breakdown */}
        <div className="grid grid-cols-3 gap-3">
          {Object.entries(data.by_direction).map(([dir, stats]) => {
            const info = DIRECTION_LABELS[dir];
            if (!info) return null;
            const Icon = info.icon;
            return (
              <div key={dir} className="text-center p-2 rounded-md bg-muted/50">
                <div className="flex items-center justify-center gap-1 mb-1">
                  <Icon className="size-3" />
                  <span className="text-xs font-medium">{info.label}</span>
                </div>
                <AccuracyBadge pct={stats.accuracy_pct} />
                <p className="text-xs text-muted-foreground mt-1">
                  {stats.correct}/{stats.total}
                </p>
              </div>
            );
          })}
        </div>

        {/* Per-timeframe breakdown */}
        {data.by_timeframe && Object.keys(data.by_timeframe).length > 0 && (
          <div className="border-t pt-3">
            <p className="text-xs font-medium text-muted-foreground mb-2">Theo khung thời gian</p>
            <div className="flex gap-4">
              {Object.entries(data.by_timeframe).map(([tf, stats]) => (
                <div key={tf} className="text-center">
                  <span className="text-xs text-muted-foreground">{tf}</span>
                  <div className="mt-0.5">
                    <AccuracyBadge pct={stats.accuracy_pct} />
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
