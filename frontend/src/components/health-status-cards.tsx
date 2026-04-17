"use client";

import { useJobStatuses } from "@/lib/hooks";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { CheckCircle, AlertTriangle, XCircle, Clock } from "lucide-react";

const COLOR_MAP = {
  green: { bg: "bg-green-50 dark:bg-green-950/30", border: "border-green-200 dark:border-green-800", icon: CheckCircle, iconColor: "text-green-600" },
  yellow: { bg: "bg-yellow-50 dark:bg-yellow-950/30", border: "border-yellow-200 dark:border-yellow-800", icon: AlertTriangle, iconColor: "text-yellow-600" },
  red: { bg: "bg-red-50 dark:bg-red-950/30", border: "border-red-200 dark:border-red-800", icon: XCircle, iconColor: "text-red-600" },
} as const;

function formatDuration(seconds: number | null): string {
  if (seconds === null) return "—";
  if (seconds < 60) return `${Math.round(seconds)}s`;
  return `${Math.floor(seconds / 60)}m ${Math.round(seconds % 60)}s`;
}

function formatTime(iso: string | null): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleString("vi-VN", { hour: "2-digit", minute: "2-digit", day: "2-digit", month: "2-digit" });
}

export function HealthStatusCards() {
  const { data, isLoading, error } = useJobStatuses();

  if (isLoading) {
    return (
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {Array.from({ length: 6 }).map((_, i) => (
          <Skeleton key={i} className="h-32" />
        ))}
      </div>
    );
  }

  if (error || !data) {
    return <p className="text-sm text-muted-foreground">Không thể tải trạng thái job.</p>;
  }

  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {data.jobs.map((job) => {
        const style = COLOR_MAP[job.color] ?? COLOR_MAP.red;
        const Icon = style.icon;
        return (
          <Card key={job.job_id} className={`${style.bg} ${style.border} border`}>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium flex items-center gap-2">
                <Icon className={`size-4 ${style.iconColor}`} />
                {job.job_name}
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-1 text-xs text-muted-foreground">
              <div className="flex justify-between">
                <span>Trạng thái</span>
                <Badge variant={job.color === "green" ? "default" : job.color === "yellow" ? "secondary" : "destructive"} className="text-xs">
                  {job.status}
                </Badge>
              </div>
              <div className="flex justify-between">
                <span>Lần chạy cuối</span>
                <span className="flex items-center gap-1">
                  <Clock className="size-3" />
                  {formatTime(job.started_at)}
                </span>
              </div>
              <div className="flex justify-between">
                <span>Thời gian</span>
                <span>{formatDuration(job.duration_seconds)}</span>
              </div>
              {job.error_message && (
                <p className="text-xs text-red-600 dark:text-red-400 mt-1 truncate" title={job.error_message}>
                  ⚠ {job.error_message}
                </p>
              )}
            </CardContent>
          </Card>
        );
      })}
    </div>
  );
}
