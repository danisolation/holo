"use client";

import { Badge } from "@/components/ui/badge";
import { WatchlistTable } from "@/components/watchlist-table";
import { ExchangeFilter } from "@/components/exchange-filter";
import { useWatchlistStore } from "@/lib/store";

export default function WatchlistPage() {
  const { watchlist } = useWatchlistStore();

  return (
    <div>
      <div className="flex items-center gap-3 mb-6">
        <h2 className="text-2xl font-bold tracking-tight">
          Danh mục theo dõi
        </h2>
        {watchlist.length > 0 && (
          <Badge variant="secondary">{watchlist.length} mã</Badge>
        )}
      </div>

      {/* Exchange filter */}
      <div className="mb-6">
        <ExchangeFilter />
      </div>

      <WatchlistTable />
    </div>
  );
}
