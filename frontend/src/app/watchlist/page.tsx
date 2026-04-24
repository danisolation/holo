"use client";

import { useEffect } from "react";
import { Badge } from "@/components/ui/badge";
import { WatchlistTable } from "@/components/watchlist-table";
import { useWatchlist } from "@/lib/hooks";
import { migrateLocalWatchlist } from "@/lib/store";

export default function WatchlistPage() {
  const { data: watchlistItems } = useWatchlist();

  // One-time migration from localStorage to server
  useEffect(() => {
    migrateLocalWatchlist();
  }, []);

  return (
    <div data-testid="watchlist-page">
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
    </div>
  );
}
