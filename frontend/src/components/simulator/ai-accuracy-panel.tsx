"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { formatVND } from "@/lib/format";
import { useSimulatorStats } from "@/lib/hooks";

function StatCol({
  label,
  winRate,
  avgReturn,
  totalPnl,
  highlight,
}: {
  label: string;
  winRate: number;
  avgReturn: number;
  totalPnl: number;
  highlight: boolean;
}) {
  const pnlColor = totalPnl >= 0 ? "#26a69a" : "#ef5350";
  return (
    <div
      className={`rounded-lg p-4 ${highlight ? "ring-2 ring-[#26a69a]/50 bg-[#26a69a]/5" : "bg-muted/30"}`}
    >
      <h4 className="text-sm font-semibold mb-3">{label}</h4>
      <div className="space-y-2">
        <div>
          <p className="text-xs text-muted-foreground">Tỷ lệ thắng</p>
          <p className="text-lg font-semibold">{winRate.toFixed(1)}%</p>
        </div>
        <div>
          <p className="text-xs text-muted-foreground">Lợi nhuận TB</p>
          <p className="text-lg font-semibold">
            {avgReturn >= 0 ? "+" : ""}
            {avgReturn.toFixed(2)}%
          </p>
        </div>
        <div>
          <p className="text-xs text-muted-foreground">Tổng lãi/lỗ</p>
          <p className="text-lg font-semibold" style={{ color: pnlColor }}>
            {totalPnl >= 0 ? "+" : ""}
            {formatVND(totalPnl)}
          </p>
        </div>
      </div>
    </div>
  );
}

export function AiAccuracyPanel({ portfolioType = "user" }: { portfolioType?: string }) {
  const { data, isLoading } = useSimulatorStats(portfolioType);

  if (isLoading) {
    return (
      <p className="text-sm text-muted-foreground py-6 text-center">
        Đang tải...
      </p>
    );
  }

  if (!data || data.total_trades === 0) {
    return (
      <p className="text-sm text-muted-foreground py-6 text-center">
        Chưa có dữ liệu thống kê. Hãy thực hiện giao dịch trước.
      </p>
    );
  }

  const aiBetter = data.ai_win_rate >= data.manual_win_rate;

  return (
    <Card>
      <CardHeader>
        <CardTitle>So sánh AI vs Thủ công</CardTitle>
      </CardHeader>
      <CardContent>
        {/* Summary counts */}
        <div className="grid grid-cols-3 gap-4 mb-4">
          <div className="text-center">
            <p className="text-xs text-muted-foreground">Tổng GD</p>
            <p className="text-xl font-bold">{data.total_trades}</p>
          </div>
          <div className="text-center">
            <p className="text-xs text-muted-foreground">AI</p>
            <p className="text-xl font-bold">{data.ai_trades}</p>
          </div>
          <div className="text-center">
            <p className="text-xs text-muted-foreground">Thủ công</p>
            <p className="text-xl font-bold">{data.manual_trades}</p>
          </div>
        </div>

        {/* Comparison columns */}
        <div className="grid grid-cols-2 gap-4">
          <StatCol
            label="AI"
            winRate={data.ai_win_rate}
            avgReturn={data.ai_avg_return_pct}
            totalPnl={data.ai_total_pnl}
            highlight={aiBetter}
          />
          <StatCol
            label="Thủ công"
            winRate={data.manual_win_rate}
            avgReturn={data.manual_avg_return_pct}
            totalPnl={data.manual_total_pnl}
            highlight={!aiBetter}
          />
        </div>
      </CardContent>
    </Card>
  );
}
