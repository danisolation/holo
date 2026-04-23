"use client";

import { useState } from "react";
import { Target } from "lucide-react";
import { Card, CardHeader, CardContent, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { useCurrentGoal } from "@/lib/hooks";
import { formatVND } from "@/lib/format";
import { SetGoalDialog } from "@/components/set-goal-dialog";

function getProgressColor(pct: number) {
  if (pct >= 100) return "green";
  if (pct >= 50) return "amber";
  return "red";
}

function getProgressBarClass(color: string) {
  if (color === "green") return "bg-[#26a69a]";
  if (color === "amber") return "bg-amber-600 dark:bg-amber-400";
  return "bg-[#ef5350]";
}

function getProgressTextClass(pct: number) {
  if (pct >= 100) return "text-[#26a69a]";
  if (pct >= 50) return "text-amber-600 dark:text-amber-400";
  if (pct > 0) return "text-[#ef5350]";
  return "text-muted-foreground";
}

function formatMonth(monthStr: string): string {
  const d = new Date(monthStr);
  return `${d.getMonth() + 1}/${d.getFullYear()}`;
}

export function MonthlyGoalCard() {
  const { data: goal, isLoading, isError } = useCurrentGoal();
  const [dialogOpen, setDialogOpen] = useState(false);

  if (isLoading) {
    return <Skeleton className="h-24 rounded-xl" />;
  }

  if (isError) {
    return (
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle className="text-base font-bold">Mục tiêu tháng</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="font-mono text-2xl font-bold text-muted-foreground">—</p>
        </CardContent>
      </Card>
    );
  }

  if (!goal) {
    return (
      <>
        <Card>
          <CardContent className="flex flex-col items-center text-center py-8">
            <Target className="size-8 text-muted-foreground/40 mx-auto mb-2" />
            <p className="text-sm font-bold">Chưa đặt mục tiêu tháng này</p>
            <p className="text-xs text-muted-foreground mt-1">
              Đặt mục tiêu lợi nhuận để theo dõi tiến độ.
            </p>
            <Button
              variant="default"
              size="sm"
              className="mt-3"
              onClick={() => setDialogOpen(true)}
            >
              Đặt mục tiêu
            </Button>
          </CardContent>
        </Card>
        <SetGoalDialog
          open={dialogOpen}
          onOpenChange={setDialogOpen}
        />
      </>
    );
  }

  const pct = goal.progress_pct;
  const roundedPct = Math.round(pct);
  const color = getProgressColor(pct);
  const barClass = getProgressBarClass(color);
  const textClass = getProgressTextClass(pct);
  const pctPrefix = pct >= 100 ? "🎉 " : "";
  const actualColor = goal.actual_pnl >= 0 ? "text-[#26a69a]" : "text-[#ef5350]";
  const actualSign = goal.actual_pnl > 0 ? "+" : goal.actual_pnl < 0 ? "-" : "";
  const actualDisplay = actualSign + formatVND(Math.abs(goal.actual_pnl));

  return (
    <>
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle className="text-base font-bold">
            Mục tiêu tháng {formatMonth(goal.month)}
          </CardTitle>
          <Button
            variant="outline"
            size="sm"
            onClick={() => setDialogOpen(true)}
          >
            Thay đổi
          </Button>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-between">
            <div className="flex items-baseline gap-1 min-w-0">
              <span className={`font-mono text-2xl font-bold ${actualColor}`}>
                {actualDisplay}
              </span>
              <span className="text-muted-foreground"> / </span>
              <span className="font-mono text-sm text-muted-foreground">
                {formatVND(goal.target_pnl)} VND
              </span>
            </div>
            <span className={`font-mono text-sm font-bold ${textClass} shrink-0 ml-2`}>
              {pctPrefix}{roundedPct}%
            </span>
          </div>
          <div className="h-2 rounded-full bg-muted w-full mt-3">
            <div
              role="progressbar"
              aria-valuenow={roundedPct}
              aria-valuemin={0}
              aria-valuemax={100}
              aria-label="Tiến độ mục tiêu tháng"
              className={`h-full rounded-full transition-all duration-500 ${barClass}`}
              style={{ width: `${Math.min(pct, 100)}%` }}
            />
          </div>
        </CardContent>
      </Card>
      <SetGoalDialog
        open={dialogOpen}
        onOpenChange={setDialogOpen}
        currentTarget={goal.target_pnl}
      />
    </>
  );
}
