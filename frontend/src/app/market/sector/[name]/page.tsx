"use client";

import { use } from "react";
import { useRouter } from "next/navigation";
import { ArrowLeft, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useSectorDetail } from "@/lib/hooks";
import { SectorDetailTable } from "@/components/market/sector-detail-table";
import { SectorPerformanceChart } from "@/components/market/sector-performance-chart";
import { PeerComparisonSection } from "@/components/market/peer-comparison-section";

export default function SectorDetailPage({
  params,
}: {
  params: Promise<{ name: string }>;
}) {
  const { name } = use(params);
  const decodedName = decodeURIComponent(name);
  const router = useRouter();

  const { data, isLoading, error, refetch } = useSectorDetail(decodedName);

  if (isLoading) {
    return (
      <div className="container mx-auto p-4 space-y-6">
        <div className="flex items-center gap-3">
          <Skeleton className="h-9 w-9 rounded-md" />
          <Skeleton className="h-8 w-64" />
        </div>
        <Skeleton className="h-[300px] rounded-xl" />
        <Skeleton className="h-[400px] rounded-xl" />
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="container mx-auto p-4">
        <Card>
          <CardContent className="flex flex-col items-center gap-4 py-12">
            <p className="text-destructive">
              Không thể tải dữ liệu ngành
            </p>
            <div className="flex gap-2">
              <Button variant="outline" onClick={() => router.push("/market")}>
                <ArrowLeft className="size-4 mr-1" />
                Quay lại
              </Button>
              <Button variant="outline" onClick={() => refetch()}>
                <RefreshCw className="size-4 mr-1" />
                Thử lại
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="container mx-auto p-4 space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <Button
          variant="ghost"
          size="icon"
          onClick={() => router.push("/market")}
        >
          <ArrowLeft className="size-5" />
        </Button>
        <h2 className="text-2xl font-bold">{data.sector}</h2>
        <Badge variant="secondary">{data.ticker_count} mã</Badge>
      </div>

      {/* Performance chart */}
      <SectorPerformanceChart tickers={data.tickers} />

      {/* Ticker table */}
      <Card>
        <CardContent className="pt-4">
          <h3 className="text-lg font-semibold mb-3">
            Danh sách cổ phiếu
          </h3>
          <SectorDetailTable tickers={data.tickers} />
        </CardContent>
      </Card>

      {/* Peer comparison */}
      <Card>
        <CardContent className="pt-4">
          <h3 className="text-lg font-semibold mb-3">
            So sánh cùng ngành
          </h3>
          <PeerComparisonSection sectorTickers={data.tickers} />
        </CardContent>
      </Card>
    </div>
  );
}
