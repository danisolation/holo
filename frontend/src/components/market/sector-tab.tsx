"use client";

import { useSectorPerformance } from "@/lib/hooks";
import { Skeleton } from "@/components/ui/skeleton";
import { SectorHeatmap } from "./sector-heatmap";
import { SectorRanking } from "./sector-ranking";

export function SectorTab() {
  const { data, isLoading, error } = useSectorPerformance();

  if (isLoading)
    return (
      <div className="space-y-4">
        <div className="grid grid-cols-3 md:grid-cols-5 gap-2">
          {Array.from({ length: 15 }).map((_, i) => (
            <Skeleton key={i} className="h-20 rounded-md" />
          ))}
        </div>
        <Skeleton className="h-64 rounded-md" />
      </div>
    );

  if (error || !data)
    return (
      <p className="text-sm text-destructive text-center py-8">
        Không thể tải dữ liệu ngành
      </p>
    );

  return (
    <div className="space-y-6">
      <SectorHeatmap sectors={data} />
      <SectorRanking sectors={data} />
    </div>
  );
}
