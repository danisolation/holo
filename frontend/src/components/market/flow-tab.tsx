"use client";

import { useMemo } from "react";
import { useSectorPerformance, useSectorFlow } from "@/lib/hooks";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { SectorRadar } from "@/components/market/sector-radar";
import type { SectorFlowItem } from "@/lib/api";

/** Get the latest flow entry per sector, sorted by net_volume descending */
function getLatestFlowBySector(items: SectorFlowItem[]) {
  const latest = new Map<string, SectorFlowItem>();
  for (const item of items) {
    const existing = latest.get(item.sector);
    if (!existing || item.date > existing.date) {
      latest.set(item.sector, item);
    }
  }
  return Array.from(latest.values()).sort((a, b) => b.net_volume - a.net_volume);
}

function formatVolume(v: number): string {
  const abs = Math.abs(v);
  if (abs >= 1_000_000_000) return `${(v / 1_000_000_000).toFixed(1)}tỷ`;
  if (abs >= 1_000_000) return `${(v / 1_000_000).toFixed(1)}tr`;
  if (abs >= 1_000) return `${(v / 1_000).toFixed(0)}k`;
  return v.toLocaleString("vi-VN");
}

export function FlowTab() {
  const {
    data: sectorData,
    isLoading: sectorLoading,
    isError: sectorError,
  } = useSectorPerformance();

  const {
    data: flowData,
    isLoading: flowLoading,
    isError: flowError,
  } = useSectorFlow();

  const latestFlow = useMemo(() => {
    if (!flowData) return [];
    return getLatestFlowBySector(flowData);
  }, [flowData]);

  const maxAbsVolume = useMemo(() => {
    if (!latestFlow.length) return 1;
    return Math.max(...latestFlow.map((f) => Math.abs(f.net_volume)), 1);
  }, [latestFlow]);

  const isLoading = sectorLoading || flowLoading;
  const isError = sectorError || flowError;

  if (isError) {
    return (
      <div className="text-sm text-destructive text-center py-12">
        Không thể tải dữ liệu dòng tiền. Vui lòng thử lại sau.
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-[480px] w-full rounded-lg" />
        <Skeleton className="h-[300px] w-full rounded-lg" />
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Radar chart */}
      {sectorData && sectorData.length > 0 && (
        <SectorRadar sectors={sectorData} />
      )}

      {/* Flow summary */}
      {latestFlow.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Dòng tiền ròng theo ngành</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {latestFlow.map((item) => {
                const isPositive = item.net_volume >= 0;
                const widthPct = Math.max(
                  (Math.abs(item.net_volume) / maxAbsVolume) * 100,
                  2
                );
                return (
                  <div key={item.sector} className="flex items-center gap-3">
                    <span className="text-sm w-28 flex-shrink-0 truncate" title={item.sector}>
                      {item.sector}
                    </span>
                    <div className="flex-1 flex items-center">
                      {isPositive ? (
                        <div className="flex items-center w-full">
                          <div
                            className="h-5 rounded-sm"
                            style={{
                              width: `${widthPct}%`,
                              backgroundColor: "#26a69a",
                              minWidth: "4px",
                            }}
                          />
                        </div>
                      ) : (
                        <div className="flex items-center justify-end w-full">
                          <div
                            className="h-5 rounded-sm"
                            style={{
                              width: `${widthPct}%`,
                              backgroundColor: "#ef5350",
                              minWidth: "4px",
                            }}
                          />
                        </div>
                      )}
                    </div>
                    <span
                      className="text-sm font-medium w-16 text-right flex-shrink-0"
                      style={{ color: isPositive ? "#26a69a" : "#ef5350" }}
                    >
                      {isPositive ? "+" : ""}
                      {formatVolume(item.net_volume)}
                    </span>
                  </div>
                );
              })}
            </div>
            <p className="text-xs text-muted-foreground mt-3">
              <span style={{ color: "#26a69a" }}>■</span> Mua ròng &nbsp;
              <span style={{ color: "#ef5350" }}>■</span> Bán ròng
            </p>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
