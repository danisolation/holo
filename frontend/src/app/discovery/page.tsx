"use client";

import Link from "next/link";
import { Search } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { DiscoveryTable } from "@/components/discovery-table";
import { useDiscovery } from "@/lib/hooks";

export default function DiscoveryPage() {
  const { data } = useDiscovery();

  return (
    <div data-testid="discovery-page">
      <h2 className="text-2xl font-bold tracking-tight mb-2">
        Khám phá cổ phiếu
      </h2>
      {data && data.length === 0 ? (
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
