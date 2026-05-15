"use client";

import { useState } from "react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell,
} from "@/components/ui/table";
import { usePeerComparison } from "@/lib/hooks";
import { PeerRadarChart } from "./peer-radar-chart";
import type { SectorDetailTickerItem } from "@/lib/api";

interface PeerComparisonSectionProps {
  sectorTickers: SectorDetailTickerItem[];
}

function formatChange(val: number | null) {
  if (val == null) return "—";
  const color = val > 0 ? "var(--trading-bull)" : val < 0 ? "var(--trading-bear)" : undefined;
  return (
    <span style={{ color }}>
      {val > 0 ? "+" : ""}
      {val.toFixed(2)}%
    </span>
  );
}

function formatMarketCap(val: number | null) {
  if (val == null) return "—";
  return (val / 1e9).toFixed(1) + " tỷ";
}

function RankBadge({ rank }: { rank: number | null }) {
  if (rank == null) return <span>—</span>;
  const variant = rank <= 3 ? "default" : "secondary";
  return <Badge variant={variant}>#{rank}</Badge>;
}

export function PeerComparisonSection({
  sectorTickers,
}: PeerComparisonSectionProps) {
  const [selectedSymbol, setSelectedSymbol] = useState<string | null>(null);

  const { data, isLoading, error } = usePeerComparison(
    selectedSymbol ?? undefined
  );

  const quickPicks = sectorTickers.slice(0, 10);

  return (
    <div className="space-y-4">
      {/* Quick select chips */}
      <div className="flex flex-wrap gap-2">
        {quickPicks.map((t) => (
          <Button
            key={t.symbol}
            variant={selectedSymbol === t.symbol ? "default" : "outline"}
            size="sm"
            onClick={() => setSelectedSymbol(t.symbol)}
          >
            {t.symbol}
          </Button>
        ))}
      </div>

      {!selectedSymbol && (
        <p className="text-muted-foreground text-sm py-4">
          Chọn một mã để so sánh với ngành
        </p>
      )}

      {selectedSymbol && isLoading && (
        <div className="space-y-3">
          <Skeleton className="h-[200px] rounded-xl" />
          <Skeleton className="h-[350px] rounded-xl" />
        </div>
      )}

      {selectedSymbol && error && (
        <p className="text-destructive text-sm py-4">
          Không thể tải dữ liệu so sánh cho {selectedSymbol}
        </p>
      )}

      {data && data.peers.length > 0 && (
        <>
          {/* Peer table */}
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Mã</TableHead>
                <TableHead>Giá</TableHead>
                <TableHead>KL</TableHead>
                <TableHead>%1D</TableHead>
                <TableHead>P/E</TableHead>
                <TableHead>Vốn hóa</TableHead>
                <TableHead>Rank P/E</TableHead>
                <TableHead>Rank KL</TableHead>
                <TableHead>Rank %</TableHead>
                <TableHead>Rank Vốn hóa</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {data.peers.map((peer) => (
                <TableRow
                  key={peer.symbol}
                  className={peer.is_target ? "bg-primary/10" : ""}
                >
                  <TableCell>
                    <Link
                      href={`/ticker/${peer.symbol}`}
                      className="text-primary hover:underline font-mono"
                    >
                      {peer.symbol}
                    </Link>
                    {peer.is_target && (
                      <Badge variant="outline" className="ml-1 text-[10px]">
                        Đang chọn
                      </Badge>
                    )}
                  </TableCell>
                  <TableCell>
                    {peer.close != null ? peer.close.toLocaleString() : "—"}
                  </TableCell>
                  <TableCell>
                    {peer.volume != null
                      ? peer.volume.toLocaleString("vi-VN")
                      : "—"}
                  </TableCell>
                  <TableCell>{formatChange(peer.change_1d)}</TableCell>
                  <TableCell>
                    {peer.pe != null ? peer.pe.toFixed(1) : "—"}
                  </TableCell>
                  <TableCell>{formatMarketCap(peer.market_cap)}</TableCell>
                  <TableCell>
                    <RankBadge rank={peer.rank_pe} />
                  </TableCell>
                  <TableCell>
                    <RankBadge rank={peer.rank_volume} />
                  </TableCell>
                  <TableCell>
                    <RankBadge rank={peer.rank_change} />
                  </TableCell>
                  <TableCell>
                    <RankBadge rank={peer.rank_market_cap} />
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>

          {/* Radar chart */}
          <div className="mt-4">
            <h4 className="text-sm font-semibold mb-2">
              So sánh {data.symbol} vs TB ngành
            </h4>
            <PeerRadarChart
              peers={data.peers}
              targetSymbol={data.symbol}
            />
          </div>
        </>
      )}
    </div>
  );
}
