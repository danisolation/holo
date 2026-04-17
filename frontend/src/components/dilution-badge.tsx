import { AlertTriangle } from "lucide-react";
import { Badge } from "@/components/ui/badge";

interface DilutionBadgeProps {
  dilutionPct: number;
  ratio: number;
  exDate: string;
}

function formatDateVN(dateStr: string): string {
  const d = new Date(dateStr);
  return `${String(d.getDate()).padStart(2, "0")}/${String(d.getMonth() + 1).padStart(2, "0")}/${d.getFullYear()}`;
}

export function DilutionBadge({ dilutionPct, ratio, exDate }: DilutionBadgeProps) {
  return (
    <Badge
      variant="outline"
      className="h-5 text-xs border-[var(--event-rights-issue)] text-[var(--event-rights-issue)] bg-[var(--event-rights-issue)]/10 gap-1"
      title={`Quyền mua ${ratio}:100 — Ex-date: ${formatDateVN(exDate)}`}
    >
      <AlertTriangle className="size-3" />
      <span className="font-mono">Pha loãng {dilutionPct.toFixed(1)}%</span>
    </Badge>
  );
}
