"use client";

import { useState } from "react";
import { Users, CheckCircle2, XCircle, RefreshCw, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { usePeerAnalysis } from "@/lib/hooks";

/**
 * AI Peer Analysis Panel — Phase 106.
 *
 * Lazy: only fetches when user clicks the trigger button.
 * Displays structured Vietnamese AI analysis comparing ticker to sector peers.
 */
export function PeerAnalysisPanel({ symbol }: { symbol: string }) {
  const [showPanel, setShowPanel] = useState(false);
  const { data, isLoading, isFetching, error, refetch } = usePeerAnalysis(symbol);

  const handleClick = () => {
    setShowPanel(true);
    refetch();
  };

  // Color-code verdict
  const getVerdictColor = (verdict: string) => {
    const lower = verdict.toLowerCase();
    if (lower.includes("vượt trội") || lower.includes("tốt") || lower.includes("mạnh")) {
      return "text-emerald-600 dark:text-emerald-400";
    }
    if (lower.includes("thua") || lower.includes("yếu") || lower.includes("kém")) {
      return "text-red-600 dark:text-red-400";
    }
    return "text-foreground";
  };

  // Not yet triggered — show button only
  if (!showPanel) {
    return (
      <Button
        variant="outline"
        size="sm"
        onClick={handleClick}
        className="gap-1.5"
      >
        <Users className="size-3.5" />
        Phân tích so sánh ngành
      </Button>
    );
  }

  // Loading state
  if (isLoading || isFetching) {
    return (
      <Card>
        <CardHeader className="pb-3">
          <div className="flex items-center gap-2">
            <Loader2 className="size-4 animate-spin text-primary" />
            <span className="text-sm font-medium">Đang phân tích so sánh ngành...</span>
          </div>
        </CardHeader>
        <CardContent className="space-y-3">
          <Skeleton className="h-5 w-3/4" />
          <Skeleton className="h-4 w-full" />
          <Skeleton className="h-4 w-5/6" />
          <Skeleton className="h-4 w-2/3" />
        </CardContent>
      </Card>
    );
  }

  // Error state
  if (error) {
    return (
      <Card>
        <CardContent className="flex items-center justify-between py-4">
          <p className="text-sm text-destructive">
            {error instanceof Error ? error.message : "Lỗi phân tích so sánh ngành"}
          </p>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => refetch()}
            className="gap-1 text-destructive"
          >
            <RefreshCw className="size-3" />
            Thử lại
          </Button>
        </CardContent>
      </Card>
    );
  }

  // No data
  if (!data) return null;

  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <h3 className="text-base font-semibold">
            So sánh với ngành {data.sector}
          </h3>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => refetch()}
            className="gap-1 text-xs"
          >
            <RefreshCw className="size-3" />
            Làm mới
          </Button>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Overall verdict */}
        <p className={`text-lg font-bold ${getVerdictColor(data.overall_verdict)}`}>
          {data.overall_verdict}
        </p>

        {/* Strengths */}
        {data.strengths.length > 0 && (
          <div>
            <h4 className="text-sm font-semibold text-emerald-600 dark:text-emerald-400 mb-1.5">
              Điểm mạnh
            </h4>
            <ul className="space-y-1">
              {data.strengths.map((s, i) => (
                <li key={i} className="flex items-start gap-2 text-sm">
                  <CheckCircle2 className="size-4 shrink-0 mt-0.5 text-emerald-500" />
                  <span>{s}</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Weaknesses */}
        {data.weaknesses.length > 0 && (
          <div>
            <h4 className="text-sm font-semibold text-red-600 dark:text-red-400 mb-1.5">
              Điểm yếu
            </h4>
            <ul className="space-y-1">
              {data.weaknesses.map((w, i) => (
                <li key={i} className="flex items-start gap-2 text-sm">
                  <XCircle className="size-4 shrink-0 mt-0.5 text-red-500" />
                  <span>{w}</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Peer position */}
        <div>
          <h4 className="text-sm font-semibold mb-1">Vị thế trong ngành</h4>
          <p className="text-sm text-muted-foreground">{data.peer_position}</p>
        </div>

        {/* Recommendation */}
        <div className="rounded-md bg-primary/10 p-3">
          <h4 className="text-sm font-semibold mb-1">Khuyến nghị</h4>
          <p className="text-sm">{data.recommendation}</p>
        </div>
      </CardContent>
    </Card>
  );
}
