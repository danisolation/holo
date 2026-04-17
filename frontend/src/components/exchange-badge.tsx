import { Badge } from "@/components/ui/badge";

const EXCHANGE_CLASSES: Record<string, string> = {
  HOSE: "border-[var(--exchange-hose)] text-[var(--exchange-hose-fg)] bg-[var(--exchange-hose)]/10",
  HNX: "border-[var(--exchange-hnx)] text-[var(--exchange-hnx-fg)] bg-[var(--exchange-hnx)]/10",
  UPCOM: "border-[var(--exchange-upcom)] text-[var(--exchange-upcom-fg)] bg-[var(--exchange-upcom)]/10",
};

interface ExchangeBadgeProps {
  exchange: string;
}

export function ExchangeBadge({ exchange }: ExchangeBadgeProps) {
  const className = EXCHANGE_CLASSES[exchange] ?? "";

  return (
    <Badge
      variant="outline"
      className={`h-5 text-xs font-semibold uppercase ${className}`}
    >
      {exchange}
    </Badge>
  );
}
