"use client";

import { type ConnectionStatus } from "@/lib/use-realtime-prices";

interface ConnectionStatusIndicatorProps {
  status: ConnectionStatus;
  subscribedCount: number;
}

const STATUS_CONFIG: Record<
  ConnectionStatus,
  { color: string; pulse: boolean; label: string; tooltipStatus: string }
> = {
  connected: {
    color: "bg-green-500",
    pulse: true,
    label: "Live",
    tooltipStatus: "đang hoạt động",
  },
  reconnecting: {
    color: "bg-yellow-500",
    pulse: false,
    label: "Đang kết nối...",
    tooltipStatus: "đang kết nối lại",
  },
  disconnected: {
    color: "bg-red-500",
    pulse: false,
    label: "Mất kết nối",
    tooltipStatus: "mất kết nối",
  },
  market_closed: {
    color: "bg-muted-foreground",
    pulse: false,
    label: "Thị trường đóng",
    tooltipStatus: "thị trường đóng cửa",
  },
};

export function ConnectionStatusIndicator({
  status,
  subscribedCount,
}: ConnectionStatusIndicatorProps) {
  const config = STATUS_CONFIG[status];
  const tooltipText = `Kết nối WebSocket: ${config.tooltipStatus} • ${subscribedCount} mã đang theo dõi`;

  return (
    <div
      className="flex items-center gap-1.5"
      title={tooltipText}
      aria-label={tooltipText}
      role="status"
    >
      {/* 8px colored circle */}
      <span
        className={`inline-block size-2 rounded-full ${config.color}${config.pulse ? " animate-pulse" : ""}`}
      />
      {/* Label: hidden on mobile (below sm), 12px regular */}
      <span className="hidden sm:inline text-xs text-muted-foreground">
        {config.label}
      </span>
    </div>
  );
}
