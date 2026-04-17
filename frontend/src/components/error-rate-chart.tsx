"use client";

import { useErrorRates } from "@/lib/hooks";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { AreaChart, Area, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { TrendingDown } from "lucide-react";

export function ErrorRateChart() {
  const { data, isLoading, error } = useErrorRates();

  if (isLoading) return <Skeleton className="h-64" />;
  if (error || !data) return <p className="text-sm text-muted-foreground">Không thể tải error rates.</p>;

  if (data.jobs.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-medium flex items-center gap-2">
            <TrendingDown className="size-4" />
            Tỷ lệ lỗi (7 ngày)
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">Chưa có dữ liệu chạy job.</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm font-medium flex items-center gap-2">
          <TrendingDown className="size-4" />
          Tỷ lệ lỗi (7 ngày)
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {data.jobs.map((job) => (
            <div key={job.job_id} className="space-y-2">
              <div className="flex justify-between items-center">
                <span className="text-xs font-medium truncate">{job.job_name}</span>
                <span className="text-xs text-muted-foreground">
                  {job.total_failures}/{job.total_runs} lỗi
                </span>
              </div>
              <ResponsiveContainer width="100%" height={60}>
                <AreaChart data={job.days}>
                  <defs>
                    <linearGradient id={`grad-${job.job_id}`} x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor={job.total_failures > 0 ? "#ef4444" : "#22c55e"} stopOpacity={0.3} />
                      <stop offset="95%" stopColor={job.total_failures > 0 ? "#ef4444" : "#22c55e"} stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <XAxis dataKey="day" hide />
                  <YAxis hide />
                  <Tooltip
                    contentStyle={{ fontSize: 11 }}
                    formatter={(value, name) => [String(value), name === "failed" ? "Lỗi" : "Tổng"]}
                    labelFormatter={(label) => `Ngày: ${label}`}
                  />
                  <Area
                    type="monotone"
                    dataKey="failed"
                    stroke={job.total_failures > 0 ? "#ef4444" : "#22c55e"}
                    fill={`url(#grad-${job.job_id})`}
                    strokeWidth={1.5}
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
