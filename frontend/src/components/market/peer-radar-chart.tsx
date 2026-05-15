"use client";

import { useMemo } from "react";
import {
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Radar,
  ResponsiveContainer,
  Legend,
  Tooltip,
} from "recharts";
import type { PeerComparisonItem } from "@/lib/api";

interface PeerRadarChartProps {
  peers: PeerComparisonItem[];
  targetSymbol: string;
}

interface RadarDatum {
  dimension: string;
  target: number;
  peerAvg: number;
}

function normalize(
  value: number | null,
  max: number
): number {
  if (value == null || max === 0) return 0;
  return Math.min(Math.abs(value) / max * 100, 100);
}

export function PeerRadarChart({ peers, targetSymbol }: PeerRadarChartProps) {
  const radarData = useMemo<RadarDatum[]>(() => {
    const target = peers.find((p) => p.is_target);
    const others = peers.filter((p) => !p.is_target);

    if (!target || others.length === 0) return [];

    // Find max for each dimension across ALL peers
    const allPeers = peers;
    const maxPe = Math.max(...allPeers.map((p) => Math.abs(p.pe ?? 0)), 1);
    const maxVolume = Math.max(...allPeers.map((p) => Math.abs(p.volume ?? 0)), 1);
    const maxChange = Math.max(...allPeers.map((p) => Math.abs(p.change_1d ?? 0)), 1);
    const maxMcap = Math.max(...allPeers.map((p) => Math.abs(p.market_cap ?? 0)), 1);

    // Calculate peer averages
    const avgPe =
      others.reduce((s, p) => s + (p.pe ?? 0), 0) / others.length;
    const avgVolume =
      others.reduce((s, p) => s + (p.volume ?? 0), 0) / others.length;
    const avgChange =
      others.reduce((s, p) => s + (p.change_1d ?? 0), 0) / others.length;
    const avgMcap =
      others.reduce((s, p) => s + (p.market_cap ?? 0), 0) / others.length;

    return [
      {
        dimension: "P/E",
        target: normalize(target.pe, maxPe),
        peerAvg: normalize(avgPe, maxPe),
      },
      {
        dimension: "Khối lượng",
        target: normalize(target.volume, maxVolume),
        peerAvg: normalize(avgVolume, maxVolume),
      },
      {
        dimension: "% Thay đổi",
        target: normalize(target.change_1d, maxChange),
        peerAvg: normalize(avgChange, maxChange),
      },
      {
        dimension: "Vốn hóa",
        target: normalize(target.market_cap, maxMcap),
        peerAvg: normalize(avgMcap, maxMcap),
      },
    ];
  }, [peers]);

  if (radarData.length === 0) {
    return (
      <p className="text-center text-muted-foreground py-4">
        Không đủ dữ liệu để hiển thị biểu đồ radar
      </p>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={350}>
      <RadarChart data={radarData}>
        <PolarGrid />
        <PolarAngleAxis dataKey="dimension" tick={{ fontSize: 12 }} />
        <PolarRadiusAxis angle={30} domain={[0, 100]} tick={false} />
        <Tooltip
          formatter={(value: unknown, name: unknown) => [
            `${Number(value).toFixed(1)}`,
            String(name),
          ]}
        />
        <Legend />
        <Radar
          name={targetSymbol}
          dataKey="target"
          stroke="#8884d8"
          fill="#8884d8"
          fillOpacity={0.3}
        />
        <Radar
          name="TB ngành"
          dataKey="peerAvg"
          stroke="#82ca9d"
          fill="#82ca9d"
          fillOpacity={0.2}
        />
      </RadarChart>
    </ResponsiveContainer>
  );
}
