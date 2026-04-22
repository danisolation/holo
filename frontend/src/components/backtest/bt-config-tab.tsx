"use client";

import { useState } from "react";
import { Play, Square, Loader2, Clock } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import {
  useBacktestLatest,
  useStartBacktest,
  useCancelBacktest,
} from "@/lib/hooks";

function formatVND(value: number): string {
  return new Intl.NumberFormat("vi-VN").format(Math.round(value));
}

function formatEta(seconds: number): string {
  if (seconds < 60) return `${Math.round(seconds)}s`;
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.round((seconds % 3600) / 60);
  if (hours > 0) return `${hours}h ${minutes}m`;
  return `${minutes}m`;
}

function statusBadge(status: string) {
  switch (status) {
    case "running":
      return (
        <span className="inline-flex items-center gap-1 rounded-full bg-blue-100 px-2.5 py-0.5 text-xs font-medium text-blue-700 dark:bg-blue-900/30 dark:text-blue-400">
          <Loader2 className="size-3 animate-spin" />
          Đang chạy
        </span>
      );
    case "completed":
      return (
        <span className="inline-flex items-center rounded-full bg-green-100 px-2.5 py-0.5 text-xs font-medium text-green-700 dark:bg-green-900/30 dark:text-green-400">
          Hoàn thành
        </span>
      );
    case "cancelled":
      return (
        <span className="inline-flex items-center rounded-full bg-orange-100 px-2.5 py-0.5 text-xs font-medium text-orange-700 dark:bg-orange-900/30 dark:text-orange-400">
          Đã hủy
        </span>
      );
    case "failed":
      return (
        <span className="inline-flex items-center rounded-full bg-red-100 px-2.5 py-0.5 text-xs font-medium text-red-700 dark:bg-red-900/30 dark:text-red-400">
          Lỗi
        </span>
      );
    default:
      return (
        <span className="inline-flex items-center rounded-full bg-gray-100 px-2.5 py-0.5 text-xs font-medium text-gray-700 dark:bg-gray-900/30 dark:text-gray-400">
          {status}
        </span>
      );
  }
}

export function BTConfigTab() {
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [initialCapital, setInitialCapital] = useState("100000000");
  const [slippagePct, setSlippagePct] = useState("0.5");

  const startMutation = useStartBacktest();
  const cancelMutation = useCancelBacktest();

  const isRunning = startMutation.data
    ? true // just started — assume running until polling kicks in
    : false;

  const { data: latestRun, isLoading: loadingLatest } = useBacktestLatest(
    isRunning || false
  );

  // Derive running state from actual latest run
  const runIsActive = latestRun?.status === "running";

  // Re-enable polling based on actual status
  const { data: polledRun } = useBacktestLatest(runIsActive);
  const currentRun = polledRun ?? latestRun;

  const handleStart = () => {
    startMutation.mutate({
      start_date: startDate,
      end_date: endDate,
      initial_capital: Number(initialCapital),
      slippage_pct: Number(slippagePct),
    });
  };

  const handleCancel = () => {
    if (currentRun) cancelMutation.mutate(currentRun.id);
  };

  // ETA calculation
  let etaText = "Đang tính...";
  if (
    currentRun &&
    currentRun.status === "running" &&
    currentRun.completed_sessions > 0
  ) {
    const elapsedS =
      (Date.now() - new Date(currentRun.created_at).getTime()) / 1000;
    const rate = currentRun.completed_sessions / elapsedS;
    if (rate > 0) {
      const remaining =
        (currentRun.total_sessions - currentRun.completed_sessions) / rate;
      etaText = formatEta(remaining);
    }
  }

  return (
    <div className="space-y-6 mt-4">
      {/* Config Form */}
      <Card data-testid="bt-config-form">
        <CardHeader>
          <CardTitle className="text-base">Cấu hình Backtest</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="max-w-lg space-y-6">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              {/* Start date */}
              <div className="space-y-2">
                <label className="text-sm font-medium">Ngày bắt đầu</label>
                <Input
                  type="date"
                  value={startDate}
                  onChange={(e) => setStartDate(e.target.value)}
                />
              </div>

              {/* End date */}
              <div className="space-y-2">
                <label className="text-sm font-medium">Ngày kết thúc</label>
                <Input
                  type="date"
                  value={endDate}
                  onChange={(e) => setEndDate(e.target.value)}
                />
              </div>

              {/* Initial capital */}
              <div className="space-y-2">
                <label className="text-sm font-medium">
                  Vốn ban đầu (VND)
                </label>
                <Input
                  type="number"
                  min={1000000}
                  value={initialCapital}
                  onChange={(e) => setInitialCapital(e.target.value)}
                  className="font-mono"
                />
              </div>

              {/* Slippage */}
              <div className="space-y-2">
                <label className="text-sm font-medium">Slippage (%)</label>
                <Input
                  type="number"
                  min={0}
                  max={5}
                  step={0.1}
                  value={slippagePct}
                  onChange={(e) => setSlippagePct(e.target.value)}
                  className="font-mono"
                />
              </div>
            </div>

            {/* Action buttons */}
            <div className="flex gap-3">
              {currentRun?.status === "running" ? (
                <Button
                  variant="destructive"
                  onClick={handleCancel}
                  disabled={cancelMutation.isPending}
                >
                  {cancelMutation.isPending ? (
                    <>
                      <Loader2 className="mr-2 size-4 animate-spin" />
                      Đang hủy...
                    </>
                  ) : (
                    <>
                      <Square className="mr-2 size-4" />
                      Hủy Backtest
                    </>
                  )}
                </Button>
              ) : (
                <Button
                  onClick={handleStart}
                  disabled={
                    startMutation.isPending || !startDate || !endDate
                  }
                >
                  {startMutation.isPending ? (
                    <>
                      <Loader2 className="mr-2 size-4 animate-spin" />
                      Đang khởi tạo...
                    </>
                  ) : (
                    <>
                      <Play className="mr-2 size-4" />
                      Chạy Backtest
                    </>
                  )}
                </Button>
              )}
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Progress section */}
      {loadingLatest ? (
        <Skeleton className="h-32 rounded-xl" />
      ) : currentRun ? (
        <Card data-testid="bt-progress">
          <CardHeader>
            <CardTitle className="text-base flex items-center justify-between">
              <span>Tiến trình</span>
              {statusBadge(currentRun.status)}
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {/* Progress bar */}
            <div className="space-y-2">
              <div className="flex items-center justify-between text-sm">
                <span className="text-muted-foreground">
                  {currentRun.completed_sessions}/{currentRun.total_sessions}{" "}
                  phiên
                </span>
                <span className="font-mono font-medium">
                  {currentRun.progress_pct.toFixed(0)}%
                </span>
              </div>
              <div className="h-2 w-full rounded-full bg-muted">
                <div
                  className="h-2 rounded-full bg-primary transition-all duration-500"
                  style={{
                    width: `${Math.min(currentRun.progress_pct, 100)}%`,
                  }}
                />
              </div>
            </div>

            {/* ETA */}
            {currentRun.status === "running" && (
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <Clock className="size-4" />
                <span>ETA: ~{etaText}</span>
              </div>
            )}

            {/* Run info */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-sm">
              <div>
                <p className="text-muted-foreground">Từ</p>
                <p className="font-medium">{currentRun.start_date}</p>
              </div>
              <div>
                <p className="text-muted-foreground">Đến</p>
                <p className="font-medium">{currentRun.end_date}</p>
              </div>
              <div>
                <p className="text-muted-foreground">Vốn</p>
                <p className="font-medium font-mono">
                  {formatVND(currentRun.initial_capital)} ₫
                </p>
              </div>
              <div>
                <p className="text-muted-foreground">Slippage</p>
                <p className="font-medium font-mono">
                  {currentRun.slippage_pct}%
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      ) : null}
    </div>
  );
}
