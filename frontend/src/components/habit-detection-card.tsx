"use client";

import { TrendingDown, Clock, Zap, CheckCircle } from "lucide-react";
import { Card, CardHeader, CardContent, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { useHabitDetections } from "@/lib/hooks";
import type { HabitDetection } from "@/lib/api";

const HABIT_CONFIG: Record<
  HabitDetection["habit_type"],
  {
    label: (count: number) => string;
    summary: (count: number) => string;
    icon: typeof TrendingDown;
    className: string;
  }
> = {
  premature_sell: {
    label: (count) => `Bán sớm (${count})`,
    summary: (count) =>
      `Bạn có xu hướng bán sớm khi lãi (${count} lần trong tháng này).`,
    icon: TrendingDown,
    className:
      "text-amber-600 bg-amber-600/10 border-transparent dark:text-amber-400 dark:bg-amber-400/10",
  },
  holding_losers: {
    label: (count) => `Giữ lâu (${count})`,
    summary: (count) =>
      `Bạn có xu hướng giữ lâu khi lỗ (${count} lần trong tháng này).`,
    icon: Clock,
    className:
      "text-amber-600 bg-amber-600/10 border-transparent dark:text-amber-400 dark:bg-amber-400/10",
  },
  impulsive_trade: {
    label: (count) => `Vội vàng (${count})`,
    summary: (count) =>
      `Bạn có xu hướng giao dịch vội sau tin tức (${count} lần trong tháng này).`,
    icon: Zap,
    className:
      "text-blue-600 bg-blue-600/10 border-transparent dark:text-blue-400 dark:bg-blue-400/10",
  },
};

export function HabitDetectionCard() {
  const { data, isLoading, isError, refetch } = useHabitDetections();

  if (isLoading) {
    return <Skeleton className="h-24 rounded-xl" />;
  }

  if (isError) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-base font-bold">
            Thói quen giao dịch
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            Không thể tải dữ liệu. Thử lại sau.
          </p>
          <Button
            variant="ghost"
            size="sm"
            className="mt-2"
            onClick={() => refetch()}
          >
            Thử lại
          </Button>
        </CardContent>
      </Card>
    );
  }

  const habits = data?.habits ?? [];
  const hasHabits = habits.some((h) => h.count > 0);

  // Find highest count habit for summary text
  const topHabit = hasHabits
    ? [...habits]
        .filter((h) => h.count > 0)
        .sort((a, b) => b.count - a.count || a.habit_type.localeCompare(b.habit_type))[0]
    : null;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base font-bold">
          Thói quen giao dịch
        </CardTitle>
      </CardHeader>
      <CardContent>
        {!hasHabits ? (
          <div className="py-4">
            <p className="text-sm text-muted-foreground">
              <CheckCircle
                className="size-5 text-[#26a69a] inline mr-2"
                aria-hidden="true"
              />
              Chưa phát hiện thói quen xấu. Tiếp tục giữ kỷ luật!
            </p>
          </div>
        ) : (
          <>
            <div className="flex flex-wrap gap-2">
              {habits
                .filter((h) => h.count > 0)
                .map((habit) => {
                  const config = HABIT_CONFIG[habit.habit_type];
                  const Icon = config.icon;
                  return (
                    <Badge
                      key={habit.habit_type}
                      className={`text-xs font-bold ${config.className}`}
                    >
                      <Icon className="size-3 mr-1" aria-hidden="true" />
                      {config.label(habit.count)}
                    </Badge>
                  );
                })}
            </div>
            {topHabit && (
              <p className="text-sm text-muted-foreground mt-3">
                {HABIT_CONFIG[topHabit.habit_type].summary(topHabit.count)}
              </p>
            )}
          </>
        )}
      </CardContent>
    </Card>
  );
}
