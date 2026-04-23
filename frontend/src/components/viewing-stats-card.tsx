"use client";

import { Eye } from "lucide-react";
import { Card, CardHeader, CardContent, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { useViewingStats } from "@/lib/hooks";

export function ViewingStatsCard() {
  const { data, isLoading, isError, refetch } = useViewingStats();

  if (isLoading) {
    return <Skeleton className="h-48 rounded-xl" />;
  }

  if (isError) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-base font-bold">
            Mã bạn hay xem
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

  const items = data?.items ?? [];

  // Sector concentration: check if top 3 tickers share same sector
  let concentrationSector: string | null = null;
  if (items.length >= 3) {
    const topSectors = items.slice(0, 3).map((i) => i.sector).filter(Boolean);
    if (topSectors.length === 3 && new Set(topSectors).size === 1) {
      concentrationSector = topSectors[0]!;
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base font-bold">
          Mã bạn hay xem
        </CardTitle>
      </CardHeader>
      <CardContent>
        {items.length === 0 ? (
          <div className="py-6 text-center">
            <Eye className="size-8 text-muted-foreground/40 mx-auto mb-2" />
            <p className="text-sm text-muted-foreground">
              Chưa có dữ liệu xem. Duyệt qua các mã để bắt đầu theo dõi.
            </p>
          </div>
        ) : (
          <>
            <ol className="space-y-2 list-none p-0">
              {items.slice(0, 10).map((item, idx) => (
                <li key={item.ticker_symbol} className="flex items-center gap-2">
                  <span className="text-xs text-muted-foreground w-6">
                    {idx + 1}.
                  </span>
                  <span className="font-mono text-sm font-bold">
                    {item.ticker_symbol}
                  </span>
                  {item.sector && (
                    <span className="text-xs text-muted-foreground ml-2 truncate">
                      {item.sector}
                    </span>
                  )}
                  <span className="font-mono text-sm text-muted-foreground ml-auto">
                    {item.view_count}{" "}
                    <span className="text-xs">lượt</span>
                  </span>
                </li>
              ))}
            </ol>
            {concentrationSector && (
              <p className="text-xs text-amber-600 dark:text-amber-400 mt-3">
                Tập trung: {concentrationSector}
              </p>
            )}
          </>
        )}
      </CardContent>
    </Card>
  );
}
