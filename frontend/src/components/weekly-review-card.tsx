"use client";

import { useState } from "react";
import { ChevronDown, ChevronUp, FileText } from "lucide-react";
import { Card, CardHeader, CardContent, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { Skeleton } from "@/components/ui/skeleton";
import { useLatestReview } from "@/lib/hooks";
import { formatVND } from "@/lib/format";

function formatDDMM(dateStr: string): string {
  const d = new Date(dateStr);
  return `${String(d.getDate()).padStart(2, "0")}/${String(d.getMonth() + 1).padStart(2, "0")}`;
}

export function WeeklyReviewCard() {
  const { data: review, isLoading, isError, refetch } = useLatestReview();
  const [expanded, setExpanded] = useState(true);

  if (isLoading) {
    return <Skeleton className="h-48 rounded-xl" />;
  }

  if (isError) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-base font-bold">Nhận xét tuần</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground py-4">
            Không thể tải nhận xét tuần. Thử lại sau.
          </p>
          <Button variant="ghost" size="sm" onClick={() => refetch()}>
            Thử lại
          </Button>
        </CardContent>
      </Card>
    );
  }

  if (!review) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-base font-bold">Nhận xét tuần</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col items-center text-center py-4">
          <FileText className="size-8 text-muted-foreground/40 mx-auto mb-2" />
          <p className="text-sm text-muted-foreground">
            Nhận xét tuần đầu tiên sẽ được tạo vào Chủ nhật tới.
          </p>
        </CardContent>
      </Card>
    );
  }

  const pnlColor =
    review.total_pnl >= 0 ? "text-[#26a69a]" : "text-[#ef5350]";
  const pnlSign = review.total_pnl > 0 ? "+" : review.total_pnl < 0 ? "-" : "";
  const pnlDisplay = `${pnlSign}${formatVND(Math.abs(review.total_pnl))} VND`;

  return (
    <Card>
      <CardHeader
        className="flex flex-row items-center justify-between cursor-pointer"
        role="button"
        aria-expanded={expanded}
        aria-controls="review-content"
        onClick={() => setExpanded(!expanded)}
      >
        <CardTitle className="text-base font-bold">
          Nhận xét tuần {formatDDMM(review.week_start)} –{" "}
          {formatDDMM(review.week_end)}
        </CardTitle>
        {expanded ? (
          <ChevronUp className="size-4 text-muted-foreground shrink-0" />
        ) : (
          <ChevronDown className="size-4 text-muted-foreground shrink-0" />
        )}
      </CardHeader>

      {expanded && (
        <CardContent id="review-content">
          <p className="text-sm leading-relaxed">{review.summary_text}</p>

          <Separator className="my-4" />

          {review.highlights.good && review.highlights.good.length > 0 && (
            <>
              <p className="text-sm font-bold mt-4">
                <span aria-hidden="true">✅ </span>Điểm tốt
              </p>
              <ul className="list-disc pl-5 space-y-1 text-sm mt-2">
                {review.highlights.good.map((item, i) => (
                  <li key={i} className="text-[#26a69a]">
                    {item}
                  </li>
                ))}
              </ul>
            </>
          )}

          {review.highlights.bad && review.highlights.bad.length > 0 && (
            <>
              <p className="text-sm font-bold mt-4">
                <span aria-hidden="true">⚠ </span>Cần cải thiện
              </p>
              <ul className="list-disc pl-5 space-y-1 text-sm mt-2">
                {review.highlights.bad.map((item, i) => (
                  <li key={i} className="text-[#ef5350]">
                    {item}
                  </li>
                ))}
              </ul>
            </>
          )}

          {review.suggestions && review.suggestions.length > 0 && (
            <>
              <Separator className="my-4" />
              <p className="text-sm font-bold mt-4">
                <span aria-hidden="true">💡 </span>Gợi ý tuần tới
              </p>
              <ul className="list-disc pl-5 space-y-1 text-sm mt-2">
                {review.suggestions.map((item, i) => (
                  <li key={i}>{item}</li>
                ))}
              </ul>
            </>
          )}

          <div className="flex items-center gap-4 text-xs text-muted-foreground mt-4 pt-4 border-t">
            <span className="sr-only">Thống kê tuần</span>
            <span>{review.trades_count} lệnh</span>
            <span className="text-[#26a69a]">{review.win_count} thắng</span>
            <span className={`font-mono font-bold ${pnlColor}`}>
              {pnlDisplay}
            </span>
          </div>
        </CardContent>
      )}
    </Card>
  );
}
