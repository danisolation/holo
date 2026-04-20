"use client";

import { Flame, Trophy, AlertTriangle } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { usePaperStreaks } from "@/lib/hooks";

export function PTStreakCards() {
  const { data, isLoading } = usePaperStreaks();

  if (isLoading) {
    return (
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <Skeleton key={i} className="h-28 rounded-xl" />
        ))}
      </div>
    );
  }

  const streaks = data ?? {
    current_win_streak: 0,
    current_loss_streak: 0,
    longest_win_streak: 0,
    longest_loss_streak: 0,
    total_trades: 0,
  };

  const lossWarning = streaks.current_loss_streak > 5;

  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
      {/* Current win streak */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">Chuỗi thắng hiện tại</CardTitle>
          <Flame className="size-4 text-[#26a69a]" />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold text-[#26a69a]">
            {streaks.current_win_streak}
          </div>
        </CardContent>
      </Card>

      {/* Current loss streak */}
      <Card className={lossWarning ? "border-destructive" : undefined}>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">Chuỗi thua hiện tại</CardTitle>
          {lossWarning ? (
            <AlertTriangle className="size-4 text-[#ef5350]" />
          ) : null}
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold text-[#ef5350]">
            {streaks.current_loss_streak}
          </div>
          {lossWarning && (
            <p className="text-xs text-[#ef5350] mt-1">
              ⚠ Cảnh báo: chuỗi thua dài!
            </p>
          )}
        </CardContent>
      </Card>

      {/* Longest win streak */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">Chuỗi thắng dài nhất</CardTitle>
          <Trophy className="size-4 text-[#26a69a]" />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold text-[#26a69a]">
            {streaks.longest_win_streak}
          </div>
        </CardContent>
      </Card>

      {/* Longest loss streak */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">Chuỗi thua dài nhất</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold text-[#ef5350]">
            {streaks.longest_loss_streak}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
