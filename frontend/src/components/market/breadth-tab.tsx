"use client";

import { useState, useMemo } from "react";
import { useMarketBreadth } from "@/lib/hooks";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { ADLineChart } from "@/components/market/ad-line-chart";
import { MABreadthChart } from "@/components/market/ma-breadth-chart";
import { HighsLowsChart } from "@/components/market/highs-lows-chart";

type Range = "7d" | "30d" | "90d";

const RANGE_OPTIONS: { value: Range; label: string }[] = [
  { value: "7d", label: "7 ngày" },
  { value: "30d", label: "30 ngày" },
  { value: "90d", label: "90 ngày" },
];

function getStartDate(range: Range): string {
  const now = new Date();
  const days = range === "7d" ? 7 : range === "30d" ? 30 : 90;
  now.setDate(now.getDate() - days);
  return now.toISOString().split("T")[0];
}

export function BreadthTab() {
  const [range, setRange] = useState<Range>("90d");

  const startDate = useMemo(() => getStartDate(range), [range]);

  const { data, isLoading, isError } = useMarketBreadth(startDate);

  if (isError) {
    return (
      <div className="text-sm text-destructive text-center py-12">
        Không thể tải dữ liệu breadth. Vui lòng thử lại sau.
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Date range selector */}
      <div className="flex gap-2">
        {RANGE_OPTIONS.map((opt) => (
          <Button
            key={opt.value}
            variant={range === opt.value ? "default" : "outline"}
            size="sm"
            onClick={() => setRange(opt.value)}
          >
            {opt.label}
          </Button>
        ))}
      </div>

      {/* Charts */}
      {isLoading ? (
        <div className="space-y-4">
          <Skeleton className="h-[380px] w-full rounded-lg" />
          <Skeleton className="h-[380px] w-full rounded-lg" />
          <Skeleton className="h-[380px] w-full rounded-lg" />
        </div>
      ) : data ? (
        <div className="space-y-4">
          <ADLineChart data={data.ad_line} />
          <MABreadthChart data={data.ma_breadth} />
          <HighsLowsChart data={data.highs_lows} />
        </div>
      ) : null}
    </div>
  );
}
