"use client";

import { useState, useMemo } from "react";
import { usePipelineTimeline } from "@/lib/hooks";
import { Card, CardContent, CardHeader, CardTitle, CardAction } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import { Timer } from "lucide-react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  ResponsiveContainer,
  Cell,
  LabelList,
} from "recharts";

function formatDuration(seconds: number | null): string {
  if (seconds === null || seconds === 0) return "0s";
  if (seconds < 60) return `${Math.round(seconds)}s`;
  const m = Math.floor(seconds / 60);
  const s = Math.round(seconds % 60);
  return s > 0 ? `${m}m ${s}s` : `${m}m`;
}

function formatDateShort(dateStr: string): string {
  const [, month, day] = dateStr.split("-");
  return `${day}/${month}`;
}

function getBarColor(status: string): string {
  if (status === "failed") return "#ef4444"; // red-500
  if (status === "partial") return "#eab308"; // yellow-500
  return "hsl(var(--primary))";
}

function getLast7Dates(): string[] {
  const dates: string[] = [];
  const now = new Date();
  for (let i = 6; i >= 0; i--) {
    const d = new Date(now);
    d.setDate(d.getDate() - i);
    dates.push(d.toISOString().slice(0, 10));
  }
  return dates;
}

interface BarLabelProps {
  x?: number;
  y?: number;
  width?: number;
  height?: number;
  value?: number | null;
}

function BarDurationLabel({ x = 0, y = 0, width = 0, height = 0, value }: BarLabelProps) {
  if (value === null || value === undefined) return null;
  return (
    <text
      x={x + width + 4}
      y={y + height / 2}
      dominantBaseline="central"
      className="text-xs fill-muted-foreground"
      style={{ fontSize: 12 }}
    >
      {formatDuration(value)}
    </text>
  );
}

export function PipelineTimeline() {
  const { data, isLoading, error } = usePipelineTimeline(7);
  const dates = useMemo(() => getLast7Dates(), []);
  const today = dates[dates.length - 1];
  const [selectedDate, setSelectedDate] = useState(today);

  const selectedRun = useMemo(() => {
    if (!data?.runs) return null;
    return data.runs.find((r) => r.date === selectedDate) ?? null;
  }, [data, selectedDate]);

  if (isLoading) return <Skeleton className="h-64" />;
  if (error || !data) {
    return (
      <p className="text-xs text-muted-foreground">
        Không thể tải pipeline timeline.
      </p>
    );
  }

  const chartData = selectedRun
    ? selectedRun.steps.map((step) => ({
        job_name: step.job_name,
        duration_seconds: step.duration_seconds ?? 0,
        status: step.status,
        raw_duration: step.duration_seconds,
      }))
    : [];

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm font-semibold flex items-center gap-2">
          <Timer className="size-4" />
          Pipeline Timeline
        </CardTitle>
        <CardAction>
          <div className="flex items-center gap-1 flex-wrap">
            {dates.map((date) => (
              <Button
                key={date}
                variant={date === selectedDate ? "default" : "ghost"}
                size="sm"
                onClick={() => setSelectedDate(date)}
                className="text-xs"
              >
                {date === today ? "Hôm nay" : formatDateShort(date)}
              </Button>
            ))}
          </div>
        </CardAction>
      </CardHeader>
      <CardContent>
        {!selectedRun || chartData.length === 0 ? (
          <p className="text-xs text-muted-foreground">
            Chưa có dữ liệu pipeline cho ngày này.
          </p>
        ) : (
          <div>
            <ResponsiveContainer width="100%" height={chartData.length * 40 + 20}>
              <BarChart
                data={chartData}
                layout="vertical"
                margin={{ top: 0, right: 60, bottom: 0, left: 0 }}
              >
                <XAxis
                  type="number"
                  tick={{ fontSize: 12 }}
                  tickFormatter={(v: number) => `${v}s`}
                />
                <YAxis
                  type="category"
                  dataKey="job_name"
                  width={120}
                  tick={{ fontSize: 12 }}
                />
                <Bar dataKey="duration_seconds" radius={[0, 4, 4, 0]} barSize={20}>
                  {chartData.map((entry, idx) => (
                    <Cell key={idx} fill={getBarColor(entry.status)} />
                  ))}
                  <LabelList
                    dataKey="raw_duration"
                    content={<BarDurationLabel />}
                  />
                </Bar>
              </BarChart>
            </ResponsiveContainer>

            <p className="text-xs font-semibold mt-2">
              Tổng: {formatDuration(selectedRun.total_seconds)}
            </p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
