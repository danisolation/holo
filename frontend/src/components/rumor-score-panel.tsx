"use client";

import type { RumorScoreData } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Shield, TrendingUp, TrendingDown, Minus } from "lucide-react";

const DIRECTION_CONFIG: Record<
  string,
  { color: string; bgColor: string; icon: React.ReactNode; label: string }
> = {
  bullish: {
    color: "text-[#26a69a]",
    bgColor: "bg-[#26a69a]/10",
    icon: <TrendingUp className="size-3" />,
    label: "TÍCH CỰC",
  },
  bearish: {
    color: "text-[#ef5350]",
    bgColor: "bg-[#ef5350]/10",
    icon: <TrendingDown className="size-3" />,
    label: "TIÊU CỰC",
  },
  neutral: {
    color: "text-amber-500",
    bgColor: "bg-amber-500/10",
    icon: <Minus className="size-3" />,
    label: "TRUNG LẬP",
  },
};

interface RumorScorePanelProps {
  data: RumorScoreData;
}

export function RumorScorePanel({ data }: RumorScorePanelProps) {
  if (data.credibility_score == null) {
    return (
      <Card>
        <CardContent className="py-8 text-center text-muted-foreground text-sm">
          Chưa có tin đồn
        </CardContent>
      </Card>
    );
  }

  const dirCfg = data.direction
    ? DIRECTION_CONFIG[data.direction.toLowerCase()] ?? null
    : null;

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="flex items-center gap-2 text-sm">
          <Shield className="size-4" />
          Tin đồn cộng đồng
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {/* Score badges */}
        <div className="flex items-center gap-2 flex-wrap">
          <Badge variant="secondary" className="gap-1">
            Độ tin cậy: {data.credibility_score}/10
          </Badge>
          {data.impact_score != null && (
            <Badge variant="secondary" className="gap-1">
              Tác động: {data.impact_score}/10
            </Badge>
          )}
        </div>

        {/* Direction badge */}
        {dirCfg && (
          <Badge
            variant="secondary"
            className={`${dirCfg.color} ${dirCfg.bgColor} gap-1`}
          >
            {dirCfg.icon}
            {dirCfg.label}
          </Badge>
        )}

        {/* Key claims */}
        {data.key_claims.length > 0 && (
          <ul className="space-y-1">
            {data.key_claims.map((claim, i) => (
              <li key={i} className="text-sm text-muted-foreground">
                • {claim}
              </li>
            ))}
          </ul>
        )}

        {/* Reasoning */}
        {data.reasoning && (
          <p className="text-sm text-muted-foreground">{data.reasoning}</p>
        )}

        {/* Scored date */}
        {data.scored_date && (
          <p className="text-[10px] text-muted-foreground/60">
            Ngày chấm: {new Date(data.scored_date).toLocaleDateString("vi-VN")}
          </p>
        )}
      </CardContent>
    </Card>
  );
}
