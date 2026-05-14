"use client";

import { useEffect } from "react";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { WatchlistTable } from "@/components/watchlist-table";
import { useWatchlist } from "@/lib/hooks";
import { migrateLocalWatchlist } from "@/lib/store";

function WatchlistSkeleton() {
  return (
    <div className="space-y-3">
      <Skeleton className="h-8 w-48" />
      {Array.from({ length: 8 }).map((_, i) => (
        <Skeleton key={i} className="h-12 w-full" />
      ))}
    </div>
  );
}

export default function WatchlistPage() {
  const { data: watchlistItems, isLoading } = useWatchlist();

  // One-time migration from localStorage to server
  useEffect(() => {
    migrateLocalWatchlist();
  }, []);

  return (
    <div data-testid="watchlist-page">
      {isLoading ? (
        <WatchlistSkeleton />
      ) : (
        <>
          <div className="flex items-center gap-3 mb-6">
            <h2 className="text-2xl font-bold tracking-tight">
              Danh mục theo dõi
            </h2>
            {(watchlistItems?.length ?? 0) > 0 && (
              <Badge variant="secondary">{watchlistItems!.length} mã</Badge>
            )}
          </div>

          <div data-testid="watchlist-table">
            <WatchlistTable />
          </div>
        </>
      )}
    </div>
  );
}
