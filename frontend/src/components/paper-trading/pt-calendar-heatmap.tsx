"use client";

import React from "react";
import { ActivityCalendar, type Activity } from "react-activity-calendar";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { usePaperCalendar } from "@/lib/hooks";
import type { CalendarDataPoint } from "@/lib/api";

const WIN_COLORS = ["#ebedf0", "#bbf7d0", "#4ade80", "#16a34a", "#166534"];
const LOSS_COLORS = ["#ebedf0", "#fecaca", "#f87171", "#dc2626", "#991b1b"];

function mapToActivities(data: CalendarDataPoint[]): Activity[] {
  const maxMag = Math.max(...data.map((d) => Math.abs(d.daily_pnl)), 1);

  const activities: Activity[] = data.map((d) => ({
    date: d.date,
    count: d.daily_pnl,
    level: Math.min(4, Math.max(1, Math.ceil((Math.abs(d.daily_pnl) / maxMag) * 4))),
  }));

  // Anchor start — one year ago
  const oneYearAgo = new Date();
  oneYearAgo.setFullYear(oneYearAgo.getFullYear() - 1);
  const startDate = oneYearAgo.toISOString().slice(0, 10);

  // Anchor end — today
  const today = new Date().toISOString().slice(0, 10);

  const dateSet = new Set(data.map((d) => d.date));

  if (!dateSet.has(startDate)) {
    activities.unshift({ date: startDate, count: 0, level: 0 });
  }
  if (!dateSet.has(today)) {
    activities.push({ date: today, count: 0, level: 0 });
  }

  return activities;
}

function renderBlock(
  block: React.ReactElement<React.SVGAttributes<SVGRectElement>>,
  activity: Activity,
) {
  if (activity.level === 0) return block;
  const colors = activity.count >= 0 ? WIN_COLORS : LOSS_COLORS;
  return React.cloneElement(block, {
    style: { ...block.props.style, fill: colors[activity.level] },
  });
}

export function PTCalendarHeatmap() {
  const { data, isLoading } = usePaperCalendar();

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg font-semibold">Lịch giao dịch</CardTitle>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <Skeleton className="h-48 w-full rounded-lg" />
        ) : !data?.length ? (
          <div className="flex items-center justify-center h-48">
            <p className="text-sm text-muted-foreground">
              Chưa có dữ liệu lịch giao dịch.
            </p>
          </div>
        ) : (
          <>
            <div className="overflow-x-auto">
              <ActivityCalendar
                data={mapToActivities(data)}
                renderBlock={renderBlock}
                blockSize={12}
                blockMargin={3}
                showWeekdayLabels={["mon", "wed", "fri"]}
                labels={{
                  months: [
                    "T1", "T2", "T3", "T4", "T5", "T6",
                    "T7", "T8", "T9", "T10", "T11", "T12",
                  ],
                  weekdays: ["CN", "T2", "T3", "T4", "T5", "T6", "T7"],
                  totalCount: "{{count}} lệnh trong {{year}}",
                  legend: { less: "Ít", more: "Nhiều" },
                }}
                theme={{
                  light: WIN_COLORS,
                  dark: ["#161b22", "#0e4429", "#006d32", "#26a641", "#39d353"],
                }}
              />
            </div>

            {/* Custom legend for win/loss */}
            <div className="flex items-center gap-4 mt-3 text-xs text-muted-foreground">
              <div className="flex items-center gap-1">
                <div
                  className="size-3 rounded-sm"
                  style={{ backgroundColor: "#16a34a" }}
                />
                <span>Lãi</span>
              </div>
              <div className="flex items-center gap-1">
                <div
                  className="size-3 rounded-sm"
                  style={{ backgroundColor: "#dc2626" }}
                />
                <span>Lỗ</span>
              </div>
            </div>
          </>
        )}
      </CardContent>
    </Card>
  );
}
