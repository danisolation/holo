"use client";

import { useState } from "react";
import {
  Target,
  ShieldCheck,
  Equal,
  TrendingUp,
  Loader2,
} from "lucide-react";
import { Card, CardHeader, CardContent, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { useWeeklyPrompt, useRespondWeeklyPrompt } from "@/lib/hooks";

type PromptResponse = "cautious" | "unchanged" | "aggressive";

export function WeeklyPromptCard() {
  const { data: prompt } = useWeeklyPrompt();
  const respond = useRespondWeeklyPrompt();
  const [clickedBtn, setClickedBtn] = useState<PromptResponse | null>(null);

  // No pending prompt → no DOM
  if (!prompt || prompt.response !== null) return null;

  const isSubmitting = respond.isPending;
  const riskLevel = prompt.risk_level_before;

  function handleRespond(response: PromptResponse) {
    if (!prompt) return;
    setClickedBtn(response);
    respond.mutate(
      { id: prompt.id, response },
      {
        onError: () => {
          setClickedBtn(null);
        },
      },
    );
  }

  const buttons: {
    response: PromptResponse;
    label: string;
    icon: typeof ShieldCheck;
    disabled?: boolean;
    title?: string;
  }[] = [
    {
      response: "cautious",
      label: "Thận trọng hơn",
      icon: ShieldCheck,
      disabled: riskLevel === 1,
      title: riskLevel === 1 ? "Đã ở mức thận trọng nhất" : undefined,
    },
    {
      response: "unchanged",
      label: "Giữ nguyên",
      icon: Equal,
    },
    {
      response: "aggressive",
      label: "Mạo hiểm hơn",
      icon: TrendingUp,
      disabled: riskLevel === 5,
      title: riskLevel === 5 ? "Đã ở mức mạo hiểm nhất" : undefined,
    },
  ];

  return (
    <Card
      className="border-blue-600/30 dark:border-blue-400/30"
      role="region"
      aria-label="Khảo sát rủi ro hàng tuần"
    >
      <CardHeader>
        <div className="flex items-center gap-2">
          <Target
            className="size-5 text-blue-600 dark:text-blue-400 shrink-0"
            aria-hidden="true"
          />
          <CardTitle className="text-base font-bold">
            Tuần này bạn muốn giao dịch thế nào?
          </CardTitle>
        </div>
        <p className="text-sm text-muted-foreground mt-1">
          Mức rủi ro hiện tại:{" "}
          <span className="font-mono font-bold">{riskLevel}/5</span>
        </p>
      </CardHeader>
      <CardContent>
        <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-2">
          {buttons.map((btn) => {
            const Icon = btn.icon;
            const isClicked = clickedBtn === btn.response;
            return (
              <Button
                key={btn.response}
                variant="outline"
                size="default"
                disabled={isSubmitting || btn.disabled}
                title={btn.title}
                onClick={() => handleRespond(btn.response)}
              >
                {isClicked && isSubmitting ? (
                  <Loader2 className="size-4 animate-spin mr-2" />
                ) : (
                  <Icon className="size-4 mr-2" aria-hidden="true" />
                )}
                {btn.label}
              </Button>
            );
          })}
        </div>
        {respond.isError && (
          <p className="text-xs text-destructive mt-2">
            Không thể gửi phản hồi. Thử lại sau.
          </p>
        )}
      </CardContent>
    </Card>
  );
}
