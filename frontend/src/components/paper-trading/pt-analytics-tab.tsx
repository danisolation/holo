"use client";

import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import {
  usePaperDirection,
  usePaperConfidence,
  usePaperRiskReward,
  usePaperProfitFactor,
} from "@/lib/hooks";
import { PTEquityChart } from "./pt-equity-chart";
import { PTStreakCards } from "./pt-streak-cards";
import { PTTimeframeCompare } from "./pt-timeframe-compare";

function formatVND(value: number): string {
  return new Intl.NumberFormat("vi-VN").format(Math.round(value));
}

/* ---------- Direction comparison ---------- */

function DirectionCard() {
  const { data, isLoading } = usePaperDirection();

  const DIRECTION_LABELS: Record<string, string> = {
    LONG: "LONG",
    BEARISH: "BEARISH",
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base font-semibold">
          So sánh hướng giao dịch
        </CardTitle>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <Skeleton className="h-32 w-full rounded-lg" />
        ) : !data?.length ? (
          <p className="text-sm text-muted-foreground">Chưa có dữ liệu.</p>
        ) : (
          <div className="space-y-4">
            {data.map((item) => (
              <div
                key={item.direction}
                className="flex items-center justify-between border-b pb-3 last:border-0 last:pb-0"
              >
                <div className="space-y-1">
                  <p className="font-semibold text-sm">
                    {DIRECTION_LABELS[item.direction] ?? item.direction}
                  </p>
                  <p className="text-xs text-muted-foreground">
                    {item.total_trades} lệnh
                  </p>
                </div>
                <div className="flex items-center gap-3">
                  <Badge variant={item.win_rate >= 50 ? "default" : "destructive"}>
                    {item.win_rate.toFixed(1)}%
                  </Badge>
                  <span
                    className={`text-sm font-mono font-semibold ${
                      item.total_pnl >= 0 ? "text-[#26a69a]" : "text-[#ef5350]"
                    }`}
                  >
                    {item.total_pnl >= 0 ? "+" : ""}
                    {formatVND(item.total_pnl)}
                  </span>
                </div>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

/* ---------- Confidence comparison ---------- */

function ConfidenceCard() {
  const { data, isLoading } = usePaperConfidence();

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base font-semibold">
          So sánh độ tin cậy
        </CardTitle>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <Skeleton className="h-32 w-full rounded-lg" />
        ) : !data?.length ? (
          <p className="text-sm text-muted-foreground">Chưa có dữ liệu.</p>
        ) : (
          <div className="space-y-4">
            {data.map((item) => (
              <div
                key={item.bracket}
                className="flex items-center justify-between border-b pb-3 last:border-0 last:pb-0"
              >
                <div className="space-y-1">
                  <p className="font-semibold text-sm">{item.bracket}</p>
                  <p className="text-xs text-muted-foreground">
                    {item.total_trades} lệnh
                  </p>
                </div>
                <div className="flex items-center gap-3">
                  <Badge variant={item.win_rate >= 50 ? "default" : "destructive"}>
                    {item.win_rate.toFixed(1)}%
                  </Badge>
                  <span
                    className={`text-sm font-mono font-semibold ${
                      item.avg_pnl >= 0 ? "text-[#26a69a]" : "text-[#ef5350]"
                    }`}
                  >
                    {item.avg_pnl >= 0 ? "+" : ""}
                    {formatVND(item.avg_pnl)}
                  </span>
                </div>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

/* ---------- Profit Factor ---------- */

function ProfitFactorCard() {
  const { data, isLoading } = usePaperProfitFactor();

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base font-semibold">Profit Factor</CardTitle>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <Skeleton className="h-32 w-full rounded-lg" />
        ) : !data ? (
          <p className="text-sm text-muted-foreground">Chưa có dữ liệu.</p>
        ) : (
          <div className="space-y-3">
            <div>
              <p className="text-xs text-muted-foreground">Profit Factor</p>
              <p
                className={`text-3xl font-bold font-mono ${
                  data.profit_factor === null
                    ? "text-muted-foreground"
                    : data.profit_factor >= 1
                      ? "text-[#26a69a]"
                      : "text-[#ef5350]"
                }`}
              >
                {data.profit_factor === null ? "∞" : data.profit_factor.toFixed(2)}
              </p>
            </div>
            <div>
              <p className="text-xs text-muted-foreground">Expected Value</p>
              <p
                className={`text-lg font-semibold font-mono ${
                  data.expected_value >= 0 ? "text-[#26a69a]" : "text-[#ef5350]"
                }`}
              >
                {data.expected_value >= 0 ? "+" : ""}
                {formatVND(data.expected_value)} ₫
              </p>
            </div>
            <div className="grid grid-cols-2 gap-2 text-sm">
              <div>
                <p className="text-xs text-muted-foreground">Lãi gộp</p>
                <p className="font-mono text-[#26a69a]">
                  +{formatVND(data.gross_profit)}
                </p>
              </div>
              <div>
                <p className="text-xs text-muted-foreground">Lỗ gộp</p>
                <p className="font-mono text-[#ef5350]">
                  {formatVND(data.gross_loss)}
                </p>
              </div>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

/* ---------- Risk:Reward ---------- */

function RiskRewardCard() {
  const { data, isLoading } = usePaperRiskReward();

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base font-semibold">Risk:Reward</CardTitle>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <Skeleton className="h-32 w-full rounded-lg" />
        ) : !data ? (
          <p className="text-sm text-muted-foreground">Chưa có dữ liệu.</p>
        ) : (
          <div className="space-y-3">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <p className="text-xs text-muted-foreground">R:R dự kiến</p>
                <p className="text-3xl font-bold font-mono">
                  {data.avg_predicted_rr.toFixed(2)}
                </p>
              </div>
              <div>
                <p className="text-xs text-muted-foreground">R:R thực tế</p>
                <p
                  className={`text-3xl font-bold font-mono ${
                    data.avg_achieved_rr >= data.avg_predicted_rr
                      ? "text-[#26a69a]"
                      : "text-[#ef5350]"
                  }`}
                >
                  {data.avg_achieved_rr.toFixed(2)}
                </p>
              </div>
            </div>
            <div className="grid grid-cols-2 gap-2 text-sm">
              <div>
                <p className="text-xs text-muted-foreground">Trên dự kiến</p>
                <p className="font-semibold text-[#26a69a]">
                  {data.trades_above_predicted} lệnh
                </p>
              </div>
              <div>
                <p className="text-xs text-muted-foreground">Dưới dự kiến</p>
                <p className="font-semibold text-[#ef5350]">
                  {data.trades_below_predicted} lệnh
                </p>
              </div>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

/* ---------- Analytics Tab Container ---------- */

export function PTAnalyticsTab() {
  return (
    <div className="space-y-6 mt-4">
      {/* 1. Equity curve — full width */}
      <PTEquityChart />

      {/* 2. Streak cards — full width (4-col grid internally) */}
      <PTStreakCards />

      {/* 3. Direction + Confidence comparison */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <DirectionCard />
        <ConfidenceCard />
      </div>

      {/* 4. Timeframe comparison — full width */}
      <PTTimeframeCompare />

      {/* 5. Profit Factor + R:R */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <ProfitFactorCard />
        <RiskRewardCard />
      </div>
    </div>
  );
}
