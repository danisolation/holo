"use client";

import { useState } from "react";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import { useScreener } from "@/lib/hooks";
import { ScreenerFilters } from "@/components/market/screener-filters";
import { ScreenerTable } from "@/components/market/screener-table";
import type { ScreenerParams } from "@/lib/api";

export default function ScreenerPage() {
  const [params, setParams] = useState<ScreenerParams>({
    limit: 50,
    offset: 0,
  });

  const { data, isLoading, error } = useScreener(params);

  function handleSort(column: string) {
    setParams((prev) => ({
      ...prev,
      sort_by: column,
      sort_order:
        prev.sort_by === column && prev.sort_order === "asc" ? "desc" : "asc",
      offset: 0,
    }));
  }

  function handlePrev() {
    setParams((prev) => ({
      ...prev,
      offset: Math.max(0, (prev.offset ?? 0) - (prev.limit ?? 50)),
    }));
  }

  function handleNext() {
    if (!data) return;
    const nextOffset = (params.offset ?? 0) + (params.limit ?? 50);
    if (nextOffset < data.total) {
      setParams((prev) => ({ ...prev, offset: nextOffset }));
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold tracking-tight">Bộ lọc cổ phiếu</h2>
        <p className="text-sm text-muted-foreground">
          Lọc và khám phá cổ phiếu theo ngành, khối lượng, biến động giá và P/E
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Bộ lọc</CardTitle>
        </CardHeader>
        <CardContent>
          <ScreenerFilters params={params} onChange={setParams} />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Kết quả</CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="space-y-2">
              {Array.from({ length: 8 }).map((_, i) => (
                <Skeleton key={i} className="h-8 w-full rounded" />
              ))}
            </div>
          ) : error ? (
            <p className="text-sm text-destructive text-center py-8">
              Không thể tải dữ liệu
            </p>
          ) : (
            <>
              <ScreenerTable
                data={data?.items ?? []}
                sortBy={params.sort_by}
                sortOrder={params.sort_order}
                onSort={handleSort}
              />

              {data && data.total > 0 && (
                <div className="flex items-center justify-between pt-4">
                  <span className="text-sm text-muted-foreground">
                    Hiển thị {(params.offset ?? 0) + 1}–
                    {(params.offset ?? 0) + data.items.length} / {data.total}
                  </span>
                  <div className="flex gap-2">
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={handlePrev}
                      disabled={(params.offset ?? 0) === 0}
                    >
                      Trước
                    </Button>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={handleNext}
                      disabled={
                        (params.offset ?? 0) + (params.limit ?? 50) >=
                        data.total
                      }
                    >
                      Sau
                    </Button>
                  </div>
                </div>
              )}
            </>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
