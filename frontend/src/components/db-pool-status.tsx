"use client";

import { useDbPool } from "@/lib/hooks";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { HardDrive } from "lucide-react";

export function DbPoolStatus() {
  const { data, isLoading, error } = useDbPool();

  if (isLoading) return <Skeleton className="h-32" />;
  if (error || !data) return <p className="text-sm text-muted-foreground">Không thể tải DB pool.</p>;

  const total = data.pool_size + data.max_overflow;
  const used = data.checked_out;
  const pct = total > 0 ? Math.round((used / total) * 100) : 0;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm font-medium flex items-center gap-2">
          <HardDrive className="size-4" />
          Connection Pool
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="flex justify-between text-sm">
          <span>Sử dụng</span>
          <span className="font-mono">{used}/{total} ({pct}%)</span>
        </div>
        <div className="w-full bg-muted rounded-full h-2">
          <div
            className={`h-2 rounded-full transition-all ${pct > 80 ? "bg-red-500" : pct > 50 ? "bg-yellow-500" : "bg-green-500"}`}
            style={{ width: `${pct}%` }}
          />
        </div>
        <div className="grid grid-cols-2 gap-2 text-xs text-muted-foreground">
          <div>Pool size: <span className="font-mono">{data.pool_size}</span></div>
          <div>Checked in: <span className="font-mono">{data.checked_in}</span></div>
          <div>Checked out: <span className="font-mono">{data.checked_out}</span></div>
          <div>Overflow: <span className="font-mono">{data.overflow}/{data.max_overflow}</span></div>
        </div>
      </CardContent>
    </Card>
  );
}
