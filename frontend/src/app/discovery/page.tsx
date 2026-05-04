"use client";

import { Badge } from "@/components/ui/badge";
import { DiscoveryTable } from "@/components/discovery-table";
import { useDiscovery } from "@/lib/hooks";

export default function DiscoveryPage() {
  const { data: discoveryItems } = useDiscovery();

  const scoreDate = discoveryItems?.[0]?.score_date;
  const formattedDate = scoreDate
    ? new Date(scoreDate).toLocaleDateString("vi-VN", {
        day: "2-digit",
        month: "2-digit",
        year: "numeric",
      })
    : null;

  return (
    <div data-testid="discovery-page">
      <div className="flex items-center gap-3 mb-2">
        <h2 className="text-2xl font-bold tracking-tight">
          Khám phá cổ phiếu
        </h2>
        {(discoveryItems?.length ?? 0) > 0 && (
          <Badge variant="secondary">{discoveryItems!.length} mã</Badge>
        )}
      </div>
      {formattedDate && (
        <p className="text-sm text-muted-foreground mb-6">
          Dữ liệu ngày {formattedDate}
        </p>
      )}
      <DiscoveryTable />
    </div>
  );
}
