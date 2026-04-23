"use client";

import { BarChart3 } from "lucide-react";
import { Card, CardHeader, CardContent, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { useSectorPreferences } from "@/lib/hooks";
import { formatVND } from "@/lib/format";

function winRateColor(rate: number): string {
  if (rate > 50) return "text-[#26a69a]";
  if (rate < 50) return "text-[#ef5350]";
  return "text-muted-foreground";
}

function pnlColor(pnl: number): string {
  if (pnl > 0) return "text-[#26a69a]";
  if (pnl < 0) return "text-[#ef5350]";
  return "text-muted-foreground";
}

function formatPnl(pnl: number): string {
  if (pnl > 0) return `+${formatVND(pnl)}`;
  if (pnl < 0) return `-${formatVND(Math.abs(pnl))}`;
  return "0";
}

export function SectorPreferencesCard() {
  const { data, isLoading, isError, refetch } = useSectorPreferences();

  if (isLoading) {
    return <Skeleton className="h-48 rounded-xl" />;
  }

  if (isError) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-base font-bold">
            Ngành bạn giao dịch tốt
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

  const sectors = data?.sectors ?? [];
  const insufficientCount = data?.insufficient_count ?? 0;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base font-bold">
          Ngành bạn giao dịch tốt
        </CardTitle>
      </CardHeader>
      <CardContent>
        {sectors.length === 0 ? (
          <div className="py-6 text-center">
            <BarChart3 className="size-8 text-muted-foreground/40 mx-auto mb-2" />
            <p className="text-sm text-muted-foreground">
              Cần ít nhất 3 giao dịch trong 1 ngành để phân tích. Hãy ghi thêm
              lệnh!
            </p>
          </div>
        ) : (
          <>
            <ol className="space-y-2 list-none p-0">
              {sectors.map((sector, idx) => (
                <li key={sector.sector} className="flex items-center gap-2">
                  <span className="text-xs text-muted-foreground w-6">
                    {idx + 1}.
                  </span>
                  <span className="text-sm font-bold truncate">
                    {sector.sector}
                  </span>
                  <span
                    className={`font-mono text-sm font-bold ml-auto ${winRateColor(sector.win_rate)}`}
                  >
                    {sector.win_rate.toFixed(1)}%
                  </span>
                  <span
                    className={`font-mono text-sm font-bold ml-4 w-28 text-right ${pnlColor(sector.net_pnl)}`}
                  >
                    {formatPnl(sector.net_pnl)}
                  </span>
                </li>
              ))}
            </ol>
            {insufficientCount > 0 && (
              <p className="text-xs text-muted-foreground mt-3">
                Chưa đủ dữ liệu: {insufficientCount} ngành (cần ≥3 giao dịch)
              </p>
            )}
          </>
        )}
      </CardContent>
    </Card>
  );
}
