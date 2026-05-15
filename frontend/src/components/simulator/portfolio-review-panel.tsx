"use client";

import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { usePortfolioReview } from "@/lib/hooks";

function ScoreBadge({ score }: { score: number }) {
  const color =
    score >= 7
      ? "bg-green-500/20 text-green-600"
      : score >= 4
        ? "bg-yellow-500/20 text-yellow-600"
        : "bg-red-500/20 text-red-600";
  return (
    <Badge className={`text-base px-3 py-1 ${color}`}>
      Điểm: {score}/10
    </Badge>
  );
}

export function PortfolioReviewPanel({ portfolioType }: { portfolioType: string }) {
  const mutation = usePortfolioReview(portfolioType);

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0">
        <CardTitle className="text-lg">🤖 AI Review</CardTitle>
        <Button
          onClick={() => mutation.mutate()}
          disabled={mutation.isPending}
          size="sm"
        >
          {mutation.isPending ? "Đang phân tích..." : "Phân tích danh mục"}
        </Button>
      </CardHeader>

      <CardContent>
        {mutation.isPending && (
          <div className="space-y-3">
            <Skeleton className="h-6 w-24" />
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-3/4" />
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-2/3" />
          </div>
        )}

        {mutation.isError && (
          <p className="text-sm text-red-500">
            Lỗi: {mutation.error instanceof Error ? mutation.error.message : "Không thể phân tích"}
          </p>
        )}

        {mutation.data && (
          <div className="space-y-4">
            <ScoreBadge score={mutation.data.score} />

            <p className="text-sm leading-relaxed">{mutation.data.overall_assessment}</p>

            {mutation.data.strengths.length > 0 && (
              <div>
                <h4 className="text-sm font-semibold mb-1">✅ Điểm mạnh</h4>
                <ul className="space-y-1">
                  {mutation.data.strengths.map((s, i) => (
                    <li key={i} className="text-sm text-green-700 dark:text-green-400 pl-4 relative before:content-['•'] before:absolute before:left-0">
                      {s}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {mutation.data.weaknesses.length > 0 && (
              <div>
                <h4 className="text-sm font-semibold mb-1">⚠️ Điểm yếu</h4>
                <ul className="space-y-1">
                  {mutation.data.weaknesses.map((w, i) => (
                    <li key={i} className="text-sm text-amber-700 dark:text-amber-400 pl-4 relative before:content-['•'] before:absolute before:left-0">
                      {w}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {mutation.data.suggestions.length > 0 && (
              <div>
                <h4 className="text-sm font-semibold mb-1">💡 Gợi ý</h4>
                <ul className="space-y-1">
                  {mutation.data.suggestions.map((s, i) => (
                    <li key={i} className="text-sm pl-4 relative before:content-['•'] before:absolute before:left-0">
                      {s}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            <div>
              <h4 className="text-sm font-semibold mb-1">🛡️ Đánh giá rủi ro</h4>
              <p className="text-sm leading-relaxed">{mutation.data.risk_assessment}</p>
            </div>
          </div>
        )}

        {!mutation.isPending && !mutation.isError && !mutation.data && (
          <p className="text-sm text-muted-foreground text-center py-4">
            Nhấn &quot;Phân tích danh mục&quot; để nhận đánh giá từ AI
          </p>
        )}
      </CardContent>
    </Card>
  );
}
