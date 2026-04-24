"use client";

import type { AnalysisResult } from "@/lib/api";
import type { StructuredCombinedData } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import {
  TrendingUp,
  TrendingDown,
  Minus,
  BarChart3,
  Globe,
  MessageSquare,
  Brain,
  Target,
  FileText,
  DollarSign,
  AlertTriangle,
  Zap,
} from "lucide-react";

const TYPE_LABELS: Record<string, { label: string; icon: React.ReactNode }> = {
  technical: { label: "Phân tích kỹ thuật", icon: <BarChart3 className="size-4" /> },
  fundamental: { label: "Phân tích cơ bản", icon: <Globe className="size-4" /> },
  sentiment: { label: "Tâm lý thị trường", icon: <MessageSquare className="size-4" /> },
  combined: { label: "Khuyến nghị tổng hợp", icon: <Brain className="size-4" /> },
  trading_signal: { label: "Kế hoạch giao dịch", icon: <Target className="size-4" /> },
};

const SIGNAL_CONFIG: Record<
  string,
  { color: string; bgColor: string; icon: React.ReactNode; label: string }
> = {
  strong_buy: {
    color: "text-[#26a69a]",
    bgColor: "bg-[#26a69a]/10",
    icon: <TrendingUp className="size-4" />,
    label: "MUA MẠNH",
  },
  buy: {
    color: "text-[#26a69a]",
    bgColor: "bg-[#26a69a]/10",
    icon: <TrendingUp className="size-4" />,
    label: "MUA",
  },
  bullish: {
    color: "text-[#26a69a]",
    bgColor: "bg-[#26a69a]/10",
    icon: <TrendingUp className="size-4" />,
    label: "TÍCH CỰC",
  },
  strong_sell: {
    color: "text-[#ef5350]",
    bgColor: "bg-[#ef5350]/10",
    icon: <TrendingDown className="size-4" />,
    label: "BÁN MẠNH",
  },
  sell: {
    color: "text-[#ef5350]",
    bgColor: "bg-[#ef5350]/10",
    icon: <TrendingDown className="size-4" />,
    label: "BÁN",
  },
  bearish: {
    color: "text-[#ef5350]",
    bgColor: "bg-[#ef5350]/10",
    icon: <TrendingDown className="size-4" />,
    label: "TIÊU CỰC",
  },
  neutral: {
    color: "text-muted-foreground",
    bgColor: "bg-muted",
    icon: <Minus className="size-4" />,
    label: "GIỮ",
  },
  hold: {
    color: "text-muted-foreground",
    bgColor: "bg-muted",
    icon: <Minus className="size-4" />,
    label: "GIỮ",
  },
  // Combined recommendation (Vietnamese)
  mua: {
    color: "text-[#26a69a]",
    bgColor: "bg-[#26a69a]/10",
    icon: <TrendingUp className="size-4" />,
    label: "MUA",
  },
  ban: {
    color: "text-[#ef5350]",
    bgColor: "bg-[#ef5350]/10",
    icon: <TrendingDown className="size-4" />,
    label: "BÁN",
  },
  giu: {
    color: "text-muted-foreground",
    bgColor: "bg-muted",
    icon: <Minus className="size-4" />,
    label: "GIỮ",
  },
  // Fundamental health signals
  strong: {
    color: "text-[#26a69a]",
    bgColor: "bg-[#26a69a]/10",
    icon: <TrendingUp className="size-4" />,
    label: "MẠNH",
  },
  good: {
    color: "text-[#26a69a]",
    bgColor: "bg-[#26a69a]/10",
    icon: <TrendingUp className="size-4" />,
    label: "TỐT",
  },
  weak: {
    color: "text-[#ef5350]",
    bgColor: "bg-[#ef5350]/10",
    icon: <TrendingDown className="size-4" />,
    label: "YẾU",
  },
  critical: {
    color: "text-[#ef5350]",
    bgColor: "bg-[#ef5350]/10",
    icon: <TrendingDown className="size-4" />,
    label: "NGUY HIỂM",
  },
  // Sentiment signals
  very_positive: {
    color: "text-[#26a69a]",
    bgColor: "bg-[#26a69a]/10",
    icon: <TrendingUp className="size-4" />,
    label: "RẤT TÍCH CỰC",
  },
  positive: {
    color: "text-[#26a69a]",
    bgColor: "bg-[#26a69a]/10",
    icon: <TrendingUp className="size-4" />,
    label: "TÍCH CỰC",
  },
  negative: {
    color: "text-[#ef5350]",
    bgColor: "bg-[#ef5350]/10",
    icon: <TrendingDown className="size-4" />,
    label: "TIÊU CỰC",
  },
  very_negative: {
    color: "text-[#ef5350]",
    bgColor: "bg-[#ef5350]/10",
    icon: <TrendingDown className="size-4" />,
    label: "RẤT TIÊU CỰC",
  },
};

function getSignalConfig(signal: string) {
  const key = signal.toLowerCase().replace(/\s+/g, "_");
  return (
    SIGNAL_CONFIG[key] ?? {
      color: "text-muted-foreground",
      bgColor: "bg-muted",
      icon: <Minus className="size-4" />,
      label: signal.toUpperCase(),
    }
  );
}

/** Score bar visualization (1-10 scale) */
export function ScoreBar({ score }: { score: number }) {
  const pct = Math.min(100, Math.max(0, (score / 10) * 100));
  const color =
    score >= 7 ? "bg-[#26a69a]" : score >= 4 ? "bg-yellow-500" : "bg-[#ef5350]";

  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-2 bg-muted rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full transition-all ${color}`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="text-xs font-mono font-bold min-w-[2ch] text-right">
        {score}
      </span>
    </div>
  );
}

interface AnalysisCardProps {
  analysis: AnalysisResult;
  type: string;
}

export function AnalysisCard({ analysis, type }: AnalysisCardProps) {
  const typeInfo = TYPE_LABELS[type] ?? {
    label: type,
    icon: <BarChart3 className="size-4" />,
  };
  const signalCfg = getSignalConfig(analysis.signal);

  return (
    <Card>
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2 text-sm">
            {typeInfo.icon}
            {typeInfo.label}
          </CardTitle>
          <Badge
            variant="secondary"
            className={`${signalCfg.color} ${signalCfg.bgColor} gap-1`}
          >
            {signalCfg.icon}
            {signalCfg.label}
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        <ScoreBar score={analysis.score} />
        <p className="text-xs text-muted-foreground leading-relaxed">
          {analysis.reasoning}
        </p>
        <div className="flex items-center justify-between text-[10px] text-muted-foreground/60">
          <span>{analysis.analysis_date}</span>
          <span>{analysis.model_version}</span>
        </div>
      </CardContent>
    </Card>
  );
}

/** Prominent combined recommendation card */
interface CombinedCardProps {
  analysis: AnalysisResult;
}

export function CombinedRecommendationCard({ analysis }: CombinedCardProps) {
  const signalCfg = getSignalConfig(analysis.signal);

  return (
    <Card className={`${signalCfg.bgColor} border-2`}>
      <CardContent className="py-4">
        <div className="flex flex-col sm:flex-row items-center gap-4">
          <div className="flex flex-col items-center gap-1">
            <span className="text-xs text-muted-foreground uppercase tracking-wider">
              Khuyến nghị
            </span>
            <div className={`text-3xl font-bold ${signalCfg.color} flex items-center gap-2`}>
              {signalCfg.icon}
              {signalCfg.label}
            </div>
            <div className="flex items-center gap-2 mt-1">
              <span className="text-xs text-muted-foreground">Độ tin cậy:</span>
              <span className="text-sm font-bold">{analysis.score}/10</span>
            </div>
          </div>
          <div className="flex-1 border-l border-border/50 pl-4 hidden sm:block">
            <p className="text-sm text-muted-foreground leading-relaxed">
              {analysis.reasoning}
            </p>
            <div className="flex items-center gap-4 mt-2 text-[10px] text-muted-foreground/60">
              <span>{analysis.analysis_date}</span>
              <span>{analysis.model_version}</span>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

/** Extract structured sections from combined analysis raw_response */
function getStructuredData(analysis: AnalysisResult): StructuredCombinedData | null {
  const raw = analysis.raw_response;
  if (
    raw &&
    typeof raw === "object" &&
    typeof raw.summary === "string" &&
    typeof raw.key_levels === "string" &&
    typeof raw.risks === "string" &&
    typeof raw.action === "string"
  ) {
    return {
      summary: raw.summary as string,
      key_levels: raw.key_levels as string,
      risks: raw.risks as string,
      action: raw.action as string,
    };
  }
  return null;
}

const COMBINED_SECTIONS = [
  { key: "summary" as const, label: "Tóm tắt", icon: <FileText className="size-4" /> },
  { key: "key_levels" as const, label: "Mức giá quan trọng", icon: <DollarSign className="size-4" /> },
  { key: "risks" as const, label: "Rủi ro", icon: <AlertTriangle className="size-4" /> },
  { key: "action" as const, label: "Hành động cụ thể", icon: <Zap className="size-4" /> },
] as const;

/** Phase 51: Structured combined recommendation card with 4 sections */
export function StructuredCombinedCard({ analysis }: CombinedCardProps) {
  const signalCfg = getSignalConfig(analysis.signal);
  const structured = getStructuredData(analysis);

  return (
    <Card className={`${signalCfg.bgColor} border-2`}>
      <CardContent className="py-4 space-y-4">
        {/* Header: Recommendation + Confidence */}
        <div className="flex flex-col sm:flex-row items-center gap-4">
          <div className="flex flex-col items-center gap-1">
            <span className="text-xs text-muted-foreground uppercase tracking-wider">
              Khuyến nghị
            </span>
            <div className={`text-3xl font-bold ${signalCfg.color} flex items-center gap-2`}>
              {signalCfg.icon}
              {signalCfg.label}
            </div>
            <div className="flex items-center gap-2 mt-1">
              <span className="text-xs text-muted-foreground">Độ tin cậy:</span>
              <span className="text-sm font-bold">{analysis.score}/10</span>
            </div>
          </div>
        </div>

        <Separator />

        {/* Structured sections or fallback */}
        {structured ? (
          <div className="space-y-4">
            {COMBINED_SECTIONS.map(({ key, label, icon }) => (
              <div key={key}>
                <div className="flex items-center gap-2 mb-1.5">
                  <span className="text-muted-foreground">{icon}</span>
                  <h4 className="text-sm font-semibold">{label}</h4>
                </div>
                <p className="text-sm text-muted-foreground leading-relaxed pl-6">
                  {structured[key]}
                </p>
              </div>
            ))}
          </div>
        ) : (
          /* Fallback for old data without raw_response */
          <p className="text-sm text-muted-foreground leading-relaxed">
            {analysis.reasoning}
          </p>
        )}

        {/* Footer: date + model */}
        <div className="flex items-center gap-4 text-[10px] text-muted-foreground/60 pt-2">
          <span>{analysis.analysis_date}</span>
          <span>{analysis.model_version}</span>
        </div>
      </CardContent>
    </Card>
  );
}
