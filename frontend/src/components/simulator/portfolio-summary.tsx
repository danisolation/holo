"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { formatVND } from "@/lib/format";
import type { SimulatorPortfolioResponse } from "@/lib/api";

function PnlValue({ value, pct }: { value: number; pct?: number }) {
  const color = value >= 0 ? "#26a69a" : "#ef5350";
  const sign = value >= 0 ? "+" : "";
  return (
    <span style={{ color }}>
      {sign}{formatVND(value)}
      {pct !== undefined && (
        <span className="text-xs ml-1">({sign}{pct.toFixed(2)}%)</span>
      )}
    </span>
  );
}

interface PortfolioSummaryProps {
  data: SimulatorPortfolioResponse;
}

export function PortfolioSummary({ data }: PortfolioSummaryProps) {
  const items = [
    { label: "Vốn ban đầu", value: formatVND(data.starting_capital) },
    { label: "Tiền mặt", value: formatVND(data.current_cash) },
    { label: "Giá trị danh mục", value: formatVND(data.total_market_value) },
    { label: "Tổng vốn", value: formatVND(data.total_equity) },
  ];

  return (
    <Card>
      <CardHeader>
        <CardTitle>Tổng quan danh mục</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
          {items.map((item) => (
            <div key={item.label}>
              <p className="text-xs text-muted-foreground">{item.label}</p>
              <p className="text-lg font-semibold">{item.value}</p>
            </div>
          ))}
        </div>
        <div className="grid grid-cols-3 gap-4 border-t pt-4">
          <div>
            <p className="text-xs text-muted-foreground">Tổng lãi/lỗ</p>
            <p className="text-lg font-semibold">
              <PnlValue value={data.total_pnl} pct={data.total_pnl_pct} />
            </p>
          </div>
          <div>
            <p className="text-xs text-muted-foreground">Lãi đã thực hiện</p>
            <p className="text-lg font-semibold">
              <PnlValue value={data.realized_pnl} />
            </p>
          </div>
          <div>
            <p className="text-xs text-muted-foreground">Lãi chưa thực hiện</p>
            <p className="text-lg font-semibold">
              <PnlValue value={data.unrealized_pnl} />
            </p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
