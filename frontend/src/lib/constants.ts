export const TRADE_STATUS_CONFIG: Record<string, { label: string; className: string }> = {
  pending:        { label: "Chờ",         className: "text-yellow-600 bg-yellow-600/10" },
  active:         { label: "Đang mở",     className: "text-blue-600 bg-blue-600/10" },
  partial_tp:     { label: "Chốt 1 phần", className: "text-cyan-600 bg-cyan-600/10" },
  closed_tp2:     { label: "Chốt TP2",    className: "text-[#26a69a] bg-[#26a69a]/10" },
  closed_sl:      { label: "Cắt lỗ",      className: "text-[#ef5350] bg-[#ef5350]/10" },
  closed_timeout: { label: "Hết hạn",     className: "text-orange-600 bg-orange-600/10" },
  closed_manual:  { label: "Đóng tay",    className: "text-gray-600 bg-gray-600/10" },
};
