"use client";

import { useEffect, useState } from "react";
import { Badge } from "@/components/ui/badge";

const STORAGE_KEY = "simulator_auto_trade";

export function AutoTradeToggle() {
  const [enabled, setEnabled] = useState(false);

  useEffect(() => {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored === "true") setEnabled(true);
  }, []);

  function toggle() {
    const next = !enabled;
    setEnabled(next);
    localStorage.setItem(STORAGE_KEY, String(next));
  }

  return (
    <div className="flex items-center gap-3">
      <button
        type="button"
        role="switch"
        aria-checked={enabled}
        onClick={toggle}
        className={`relative inline-flex h-5 w-9 shrink-0 cursor-pointer items-center rounded-full border-2 border-transparent transition-colors ${
          enabled ? "bg-[#26a69a]" : "bg-muted-foreground/30"
        }`}
      >
        <span
          className={`pointer-events-none block size-4 rounded-full bg-white shadow-lg ring-0 transition-transform ${
            enabled ? "translate-x-4" : "translate-x-0"
          }`}
        />
      </button>
      <div className="flex items-center gap-2">
        <Badge
          variant="secondary"
          className={
            enabled
              ? "bg-[#26a69a]/20 text-[#26a69a]"
              : "bg-muted text-muted-foreground"
          }
        >
          {enabled ? "Tự động" : "Thủ công"}
        </Badge>
        <span className="text-xs text-muted-foreground">
          {enabled
            ? "AI sẽ tự thực hiện giao dịch từ tín hiệu hàng ngày"
            : "Bạn tự quyết định giao dịch"}
        </span>
      </div>
    </div>
  );
}
