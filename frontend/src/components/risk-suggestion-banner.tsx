"use client";

import { AlertTriangle, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useRiskSuggestion, useRespondRiskSuggestion } from "@/lib/hooks";

export function RiskSuggestionBanner() {
  const { data: suggestion } = useRiskSuggestion();
  const respond = useRespondRiskSuggestion();

  // No pending suggestion → no banner (no DOM per UI-SPEC)
  if (!suggestion || suggestion.status !== "pending") return null;

  const isSubmitting = respond.isPending;

  return (
    <div
      role="alert"
      aria-live="polite"
      className="rounded-lg border p-4 bg-amber-600/10 border-amber-600/30 dark:bg-amber-400/10 dark:border-amber-400/30"
    >
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <AlertTriangle className="size-5 text-amber-600 dark:text-amber-400 shrink-0" />
            <span className="text-sm font-bold text-amber-600 dark:text-amber-400">
              Đề xuất giảm rủi ro
            </span>
          </div>
          <p className="text-sm text-muted-foreground mt-1">
            {suggestion.reason}. Giảm mức rủi ro từ {suggestion.current_level} xuống{" "}
            {suggestion.suggested_level} để bảo toàn vốn?
          </p>
          {respond.isError && (
            <p className="text-xs text-destructive mt-1">
              Không thể xử lý. Thử lại sau.
            </p>
          )}
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <Button
            variant="outline"
            size="sm"
            disabled={isSubmitting}
            onClick={() => respond.mutate({ id: suggestion.id, action: "reject" })}
          >
            {respond.isPending && respond.variables?.action === "reject" && (
              <Loader2 className="size-4 animate-spin mr-1" />
            )}
            Giữ nguyên
          </Button>
          <Button
            variant="default"
            size="sm"
            disabled={isSubmitting}
            onClick={() => respond.mutate({ id: suggestion.id, action: "accept" })}
          >
            {respond.isPending && respond.variables?.action === "accept" && (
              <Loader2 className="size-4 animate-spin mr-1" />
            )}
            Đồng ý giảm
          </Button>
        </div>
      </div>
    </div>
  );
}
