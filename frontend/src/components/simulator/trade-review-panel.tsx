"use client";

import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { useTradeReview } from "@/lib/hooks";

function VerdictBadge({ verdict }: { verdict: string }) {
  const color =
    verdict === "Tốt"
      ? "bg-green-500/20 text-green-600"
      : verdict === "Trung bình"
        ? "bg-yellow-500/20 text-yellow-600"
        : "bg-red-500/20 text-red-600";
  return <Badge className={color}>{verdict}</Badge>;
}

export function TradeReviewPanel({ tradeId, portfolioType }: { tradeId: number; portfolioType: string }) {
  const mutation = useTradeReview();

  return (
    <div>
      <Button
        variant="ghost"
        size="sm"
        onClick={() => mutation.mutate({ tradeId, portfolioType })}
        disabled={mutation.isPending}
        className="text-xs"
      >
        {mutation.isPending ? "Đang phân tích..." : "🔍 Review"}
      </Button>

      {mutation.isError && (
        <p className="text-xs text-red-500 mt-1">
          Lỗi: {mutation.error instanceof Error ? mutation.error.message : "Không thể phân tích"}
        </p>
      )}

      {mutation.data && (
        <div className="mt-2 p-3 rounded-lg bg-muted/50 text-sm space-y-2">
          <div className="flex items-center gap-2">
            <span className="font-semibold text-xs">Kết luận:</span>
            <VerdictBadge verdict={mutation.data.overall_verdict} />
          </div>

          <div>
            <h5 className="text-xs font-semibold">📈 Phân tích điểm vào</h5>
            <p className="text-xs leading-relaxed">{mutation.data.entry_analysis}</p>
          </div>

          <div>
            <h5 className="text-xs font-semibold">📉 Phân tích điểm ra</h5>
            <p className="text-xs leading-relaxed">{mutation.data.exit_analysis}</p>
          </div>

          {mutation.data.what_went_well.length > 0 && (
            <div>
              <h5 className="text-xs font-semibold">✅ Đúng</h5>
              <ul className="text-xs space-y-0.5">
                {mutation.data.what_went_well.map((item, i) => (
                  <li key={i} className="text-green-700 dark:text-green-400 pl-3 relative before:content-['•'] before:absolute before:left-0">
                    {item}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {mutation.data.what_could_improve.length > 0 && (
            <div>
              <h5 className="text-xs font-semibold">⚠️ Cần cải thiện</h5>
              <ul className="text-xs space-y-0.5">
                {mutation.data.what_could_improve.map((item, i) => (
                  <li key={i} className="text-amber-700 dark:text-amber-400 pl-3 relative before:content-['•'] before:absolute before:left-0">
                    {item}
                  </li>
                ))}
              </ul>
            </div>
          )}

          <div>
            <h5 className="text-xs font-semibold">📊 Mẫu hình nhận diện</h5>
            <p className="text-xs leading-relaxed">{mutation.data.pattern_identified}</p>
          </div>
        </div>
      )}
    </div>
  );
}
