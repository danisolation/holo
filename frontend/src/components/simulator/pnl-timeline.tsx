"use client";

import { usePnlTimeline } from "@/lib/hooks";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

/** Format VND number: 27000 → "27,000" */
function formatVND(value: number): string {
  return value.toLocaleString("vi-VN");
}

/** Format date "2025-01-15" → "15/01/2025" */
function formatDate(dateStr: string): string {
  const [y, m, d] = dateStr.split("-");
  return `${d}/${m}/${y}`;
}

function PnlCell({ value }: { value: number | null }) {
  if (value === null) {
    return <span className="text-muted-foreground">—</span>;
  }
  const color = value >= 0 ? "text-green-600" : "text-red-600";
  const sign = value >= 0 ? "+" : "";
  return <span className={color}>{sign}{formatVND(Math.round(value))}</span>;
}

function CumulativeCell({ value }: { value: number }) {
  const color = value > 0 ? "text-green-600" : value < 0 ? "text-red-600" : "text-muted-foreground";
  const sign = value > 0 ? "+" : "";
  return <span className={`font-medium ${color}`}>{sign}{formatVND(Math.round(value))}</span>;
}

function SourceBadge({ source }: { source: string }) {
  if (source === "ai_auto") {
    return (
      <span className="inline-flex items-center rounded-full bg-blue-100 px-2 py-0.5 text-xs font-medium text-blue-700 dark:bg-blue-900/30 dark:text-blue-400">
        AI
      </span>
    );
  }
  return (
    <span className="inline-flex items-center rounded-full bg-gray-100 px-2 py-0.5 text-xs font-medium text-gray-600 dark:bg-gray-800 dark:text-gray-400">
      Manual
    </span>
  );
}

function SideBadge({ side }: { side: string }) {
  if (side === "BUY") {
    return (
      <span className="inline-flex items-center rounded-full bg-green-100 px-2 py-0.5 text-xs font-medium text-green-700 dark:bg-green-900/30 dark:text-green-400">
        MUA
      </span>
    );
  }
  return (
    <span className="inline-flex items-center rounded-full bg-red-100 px-2 py-0.5 text-xs font-medium text-red-700 dark:bg-red-900/30 dark:text-red-400">
      BÁN
    </span>
  );
}

export function PnlTimeline() {
  const { data, isLoading } = usePnlTimeline();

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Lịch sử P&L</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground py-8 text-center">
            Đang tải dữ liệu...
          </p>
        </CardContent>
      </Card>
    );
  }

  if (!data?.entries || data.entries.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Lịch sử P&L</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground py-8 text-center">
            Chưa có giao dịch nào
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle>Lịch sử P&L</CardTitle>
        <div className="text-sm">
          Tổng P&L:{" "}
          <CumulativeCell value={data.total_realized_pnl} />
        </div>
      </CardHeader>
      <CardContent>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b text-left text-muted-foreground">
                <th className="py-2 pr-3 font-medium">Ngày</th>
                <th className="py-2 pr-3 font-medium">Mã</th>
                <th className="py-2 pr-3 font-medium">Loại</th>
                <th className="py-2 pr-3 font-medium text-right">Số lượng</th>
                <th className="py-2 pr-3 font-medium text-right">Giá</th>
                <th className="py-2 pr-3 font-medium text-right">P&L</th>
                <th className="py-2 pr-3 font-medium text-right">P&L tích lũy</th>
                <th className="py-2 font-medium">Nguồn</th>
              </tr>
            </thead>
            <tbody>
              {data.entries.map((entry) => (
                <tr key={entry.id} className="border-b last:border-0 hover:bg-muted/50">
                  <td className="py-2 pr-3 whitespace-nowrap">{formatDate(entry.trade_date)}</td>
                  <td className="py-2 pr-3 font-medium">{entry.ticker_symbol}</td>
                  <td className="py-2 pr-3"><SideBadge side={entry.side} /></td>
                  <td className="py-2 pr-3 text-right">{formatVND(entry.quantity)}</td>
                  <td className="py-2 pr-3 text-right">{formatVND(Math.round(entry.price))}</td>
                  <td className="py-2 pr-3 text-right"><PnlCell value={entry.net_pnl} /></td>
                  <td className="py-2 pr-3 text-right"><CumulativeCell value={entry.cumulative_pnl} /></td>
                  <td className="py-2"><SourceBadge source={entry.source} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </CardContent>
    </Card>
  );
}
