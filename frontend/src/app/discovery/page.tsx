"use client";

import Link from "next/link";
import { Search } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { DiscoveryTable } from "@/components/discovery-table";
import { useDiscovery } from "@/lib/hooks";

function DiscoverySkeleton() {
  return (
    <div className="space-y-3">
      <Skeleton className="h-8 w-48" />
      <div className="flex gap-3 mb-4">
        <Skeleton className="h-9 w-40" />
        <Skeleton className="h-9 w-32" />
      </div>
      {Array.from({ length: 10 }).map((_, i) => (
        <Skeleton key={i} className="h-10 w-full" />
      ))}
    </div>
  );
}

export default function DiscoveryPage() {
  const { data, isLoading } = useDiscovery();

  return (
    <div data-testid="discovery-page">
      <h2 className="text-2xl font-bold tracking-tight mb-2">
        Khám phá cổ phiếu
      </h2>
      {isLoading ? (
        <DiscoverySkeleton />
      ) : data && data.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-12 text-center">
            <Search className="size-10 text-muted-foreground mb-3" />
            <p className="text-muted-foreground font-medium mb-1">Chưa có dữ liệu khám phá</p>
            <p className="text-sm text-muted-foreground mb-4">
              Dữ liệu khám phá được cập nhật hàng ngày sau khi pipeline chạy xong.
            </p>
            <Link
              href="/watchlist"
              className="inline-flex items-center justify-center rounded-[min(var(--radius-md),12px)] border border-input bg-background px-2.5 h-7 text-[0.8rem] font-medium shadow-xs hover:bg-accent hover:text-accent-foreground transition-colors"
            >
              Xem danh mục
            </Link>
          </CardContent>
        </Card>
      ) : (
        <DiscoveryTable />
      )}
    </div>
  );
}
