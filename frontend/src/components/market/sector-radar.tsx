"use client";

import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import type { SectorPerformanceItem } from "@/lib/api";
import {
  RadarChart,
  Radar,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";

interface RadarTooltipProps {
  active?: boolean;
  payload?: Array<{ value: number; dataKey: string; payload: { fullName: string } }>;
}

function RadarTooltip({ active, payload }: RadarTooltipProps) {
  if (!active || !payload?.length) return null;
  const fullName = payload[0]?.payload?.fullName ?? "";
  const d7 = payload.find((p) => p.dataKey === "7D");
  const d30 = payload.find((p) => p.dataKey === "30D");
  return (
    <div className="rounded-md border bg-background px-3 py-2 shadow-md text-sm">
      <p className="font-medium mb-1">{fullName}</p>
      <p style={{ color: "#2196f3" }}>7 ngày: {d7?.value?.toFixed(2) ?? "—"}%</p>
      <p style={{ color: "#ff9800" }}>30 ngày: {d30?.value?.toFixed(2) ?? "—"}%</p>
    </div>
  );
}

interface SectorRadarProps {
  sectors: SectorPerformanceItem[];
}

export function SectorRadar({ sectors }: SectorRadarProps) {
  const radarData = sectors.map((s) => ({
    sector: s.sector.length > 10 ? s.sector.substring(0, 10) + "…" : s.sector,
    fullName: s.sector,
    "7D": s.avg_change_7d ?? 0,
    "30D": s.avg_change_30d ?? 0,
  }));

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Radar ngành — 7D vs 30D</CardTitle>
        <CardDescription>So sánh hiệu suất ngắn hạn giữa các ngành</CardDescription>
      </CardHeader>
      <CardContent>
        <div style={{ minHeight: 400 }}>
          <ResponsiveContainer width="100%" height={400}>
            <RadarChart data={radarData}>
              <PolarGrid />
              <PolarAngleAxis dataKey="sector" tick={{ fontSize: 11 }} />
              <PolarRadiusAxis tick={{ fontSize: 10 }} />
              <Tooltip content={<RadarTooltip />} />
              <Legend />
              <Radar
                name="7 ngày"
                dataKey="7D"
                stroke="#2196f3"
                fill="#2196f3"
                fillOpacity={0.2}
              />
              <Radar
                name="30 ngày"
                dataKey="30D"
                stroke="#ff9800"
                fill="#ff9800"
                fillOpacity={0.2}
              />
            </RadarChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  );
}
