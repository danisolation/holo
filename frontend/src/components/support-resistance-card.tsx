"use client";

import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import type { IndicatorData } from "@/lib/api";

interface SupportResistanceCardProps {
  indicatorData: IndicatorData[];
  isLoading?: boolean;
}

const fmt = (v: number) => Math.round(v).toLocaleString("vi-VN");

export function SupportResistanceCard({
  indicatorData,
  isLoading,
}: SupportResistanceCardProps) {
  if (isLoading) {
    return <Skeleton className="h-[220px] rounded-xl" />;
  }

  // Get latest row with S/R data
  const latest = indicatorData
    .filter((d) => d.pivot_point != null)
    .sort((a, b) => b.date.localeCompare(a.date))[0];

  // Empty state — no S/R data at all
  if (!latest) {
    return (
      <Card>
        <CardContent className="py-8 text-center">
          <p className="text-sm text-muted-foreground">
            Chưa đủ dữ liệu để tính hỗ trợ & kháng cự
          </p>
          <p className="text-xs text-muted-foreground/60 mt-1">
            Cần ít nhất 20 ngày giao dịch
          </p>
        </CardContent>
      </Card>
    );
  }

  // Fibonacci swing high/low derivation
  const hasFib =
    latest.fib_236 != null &&
    latest.fib_500 != null &&
    latest.fib_618 != null;
  let swingLow: number | null = null;
  let swingHigh: number | null = null;
  if (hasFib && latest.fib_236 != null && latest.fib_500 != null) {
    swingLow = Math.round(
      (latest.fib_236 * 0.5 - latest.fib_500 * 0.236) / (0.5 - 0.236)
    );
    swingHigh = Math.round(swingLow + (latest.fib_500 - swingLow) / 0.5);
  }

  // Pivot point rows (highest to lowest)
  const pivotRows: {
    label: string;
    value: number | null;
    colorClass: string;
  }[] = [
    {
      label: "Kháng cự 2",
      value: latest.resistance_2,
      colorClass: "text-[#ef5350] bg-[#ef5350]/10",
    },
    {
      label: "Kháng cự 1",
      value: latest.resistance_1,
      colorClass: "text-[#ef5350] bg-[#ef5350]/10",
    },
    {
      label: "Điểm xoay",
      value: latest.pivot_point,
      colorClass: "text-muted-foreground bg-muted",
    },
    {
      label: "Hỗ trợ 1",
      value: latest.support_1,
      colorClass: "text-[#26a69a] bg-[#26a69a]/10",
    },
    {
      label: "Hỗ trợ 2",
      value: latest.support_2,
      colorClass: "text-[#26a69a] bg-[#26a69a]/10",
    },
  ];

  // Fibonacci rows (highest to lowest)
  const fibRows: {
    label: string;
    value: number | null;
    colorClass: string;
  }[] = [
    {
      label: "Đỉnh gần nhất",
      value: swingHigh,
      colorClass: "text-[#ef5350]",
    },
    {
      label: "Fib 61.8%",
      value: latest.fib_618,
      colorClass: "text-foreground",
    },
    {
      label: "Fib 50%",
      value: latest.fib_500,
      colorClass: "text-foreground",
    },
    {
      label: "Fib 38.2%",
      value: latest.fib_382,
      colorClass: "text-foreground",
    },
    {
      label: "Fib 23.6%",
      value: latest.fib_236,
      colorClass: "text-foreground",
    },
    {
      label: "Đáy gần nhất",
      value: swingLow,
      colorClass: "text-[#26a69a]",
    },
  ];

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg font-semibold">
          Hỗ trợ & Kháng cự
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Left column — Pivot Points */}
          <div>
            <p className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground mb-2">
              ĐIỂM XOAY (PIVOT)
            </p>
            {pivotRows.map((row) =>
              row.value != null ? (
                <div
                  key={row.label}
                  className="flex items-center justify-between py-1.5"
                >
                  <span className="text-xs font-medium text-muted-foreground">
                    {row.label}
                  </span>
                  <Badge
                    variant="secondary"
                    className={`${row.colorClass} font-mono text-sm font-semibold`}
                  >
                    {fmt(row.value)}
                  </Badge>
                </div>
              ) : null
            )}
          </div>

          {/* Right column — Fibonacci */}
          <div>
            <p className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground mb-2">
              FIBONACCI (20 NGÀY)
            </p>
            {hasFib ? (
              fibRows.map((row) =>
                row.value != null ? (
                  <div
                    key={row.label}
                    className="flex items-center justify-between py-1.5"
                  >
                    <span className="text-xs font-medium text-muted-foreground">
                      {row.label}
                    </span>
                    <span
                      className={`font-mono text-sm font-semibold ${row.colorClass}`}
                    >
                      {fmt(row.value)}
                    </span>
                  </div>
                ) : null
              )
            ) : (
              <div className="flex items-center justify-center py-6">
                <p className="text-sm text-muted-foreground">
                  Cần ít nhất 20 ngày dữ liệu
                </p>
              </div>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
