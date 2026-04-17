"use client";

import { useEffect, useRef, useState, type ReactNode } from "react";

interface PriceFlashCellProps {
  value: number;
  previousValue?: number;
  children: ReactNode;
}

type FlashDirection = "up" | "down" | null;

export function PriceFlashCell({
  value,
  previousValue,
  children,
}: PriceFlashCellProps) {
  const [flash, setFlash] = useState<FlashDirection>(null);
  const prevValueRef = useRef<number | undefined>(previousValue);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Check prefers-reduced-motion
  const prefersReducedMotion =
    typeof window !== "undefined" &&
    window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  useEffect(() => {
    const prev = prevValueRef.current;
    prevValueRef.current = value;

    // Skip flash on initial render or if reduced motion
    if (prev == null || prefersReducedMotion) return;

    if (value > prev) {
      setFlash("up");
    } else if (value < prev) {
      setFlash("down");
    } else {
      return; // No change, no flash
    }

    // Clear previous timer
    if (timerRef.current) clearTimeout(timerRef.current);

    // Remove flash class after 1s (let CSS transition handle the fade)
    timerRef.current = setTimeout(() => {
      setFlash(null);
    }, 100); // Short timeout — the CSS transition-colors duration-1000 handles the fade

    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, [value, prefersReducedMotion]);

  const flashClass =
    flash === "up"
      ? "bg-green-100/60 dark:bg-green-900/30"
      : flash === "down"
        ? "bg-red-100/60 dark:bg-red-900/30"
        : "bg-transparent";

  return (
    <span
      className={`rounded px-1 -mx-1 transition-colors duration-1000 ${flashClass}`}
    >
      {children}
    </span>
  );
}
