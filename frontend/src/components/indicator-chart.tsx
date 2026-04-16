"use client";

import { useRef, useEffect } from "react";
import {
  createChart,
  LineSeries,
  HistogramSeries,
  type IChartApi,
} from "lightweight-charts";
import type { IndicatorData } from "@/lib/api";

interface IndicatorChartProps {
  indicatorData: IndicatorData[];
}

/**
 * RSI sub-chart: RSI line with overbought (70) and oversold (30) reference lines.
 */
function RSIChart({ indicatorData }: { indicatorData: IndicatorData[] }) {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const rsiData = indicatorData
      .filter((d) => d.rsi_14 != null)
      .map((d) => ({ time: d.date as string, value: d.rsi_14! }))
      .sort((a, b) => (a.time as string).localeCompare(b.time as string));

    if (rsiData.length === 0) return;

    const chart = createChart(container, {
      layout: {
        background: { color: "#0f172a" },
        textColor: "#cbd5e1",
      },
      grid: {
        vertLines: { color: "#1e293b" },
        horzLines: { color: "#1e293b" },
      },
      width: container.clientWidth,
      height: 160,
      rightPriceScale: {
        borderColor: "#334155",
        scaleMargins: { top: 0.1, bottom: 0.1 },
      },
      timeScale: {
        borderColor: "#334155",
        timeVisible: false,
      },
      crosshair: { mode: 0 },
    });

    // RSI line
    const rsiSeries = chart.addSeries(LineSeries, {
      color: "#8B5CF6",
      lineWidth: 2,
      priceLineVisible: false,
      lastValueVisible: true,
    });
    rsiSeries.setData(rsiData);

    // Overbought line (70) — create as a line series with constant data
    const overbought = chart.addSeries(LineSeries, {
      color: "rgba(239,83,80,0.4)",
      lineWidth: 1,
      lineStyle: 2,
      priceLineVisible: false,
      lastValueVisible: false,
    });
    overbought.setData(
      rsiData.map((d) => ({ time: d.time, value: 70 }))
    );

    // Oversold line (30)
    const oversold = chart.addSeries(LineSeries, {
      color: "rgba(38,166,154,0.4)",
      lineWidth: 1,
      lineStyle: 2,
      priceLineVisible: false,
      lastValueVisible: false,
    });
    oversold.setData(
      rsiData.map((d) => ({ time: d.time, value: 30 }))
    );

    chart.timeScale().fitContent();

    const observer = new ResizeObserver((entries) => {
      for (const entry of entries) {
        chart.applyOptions({ width: entry.contentRect.width });
      }
    });
    observer.observe(container);

    return () => {
      observer.disconnect();
      chart.remove();
    };
  }, [indicatorData]);

  return (
    <div>
      <h4 className="text-xs font-medium text-muted-foreground mb-1 px-1">
        RSI (14)
        <span className="ml-2 text-[10px]">
          <span className="text-[#ef5350]">70 quá mua</span>
          {" · "}
          <span className="text-[#26a69a]">30 quá bán</span>
        </span>
      </h4>
      <div ref={containerRef} className="rounded-lg overflow-hidden" />
    </div>
  );
}

/**
 * MACD sub-chart: MACD line + Signal line + Histogram.
 */
function MACDChart({ indicatorData }: { indicatorData: IndicatorData[] }) {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const macdData = [...indicatorData]
      .filter((d) => d.macd_line != null && d.macd_signal != null)
      .sort((a, b) => a.date.localeCompare(b.date));
    if (macdData.length === 0) return;

    const chart = createChart(container, {
      layout: {
        background: { color: "#0f172a" },
        textColor: "#cbd5e1",
      },
      grid: {
        vertLines: { color: "#1e293b" },
        horzLines: { color: "#1e293b" },
      },
      width: container.clientWidth,
      height: 160,
      rightPriceScale: {
        borderColor: "#334155",
      },
      timeScale: {
        borderColor: "#334155",
        timeVisible: false,
      },
      crosshair: { mode: 0 },
    });

    // MACD Histogram
    const histogramSeries = chart.addSeries(HistogramSeries, {
      priceLineVisible: false,
      lastValueVisible: false,
    });
    histogramSeries.setData(
      macdData
        .filter((d) => d.macd_histogram != null)
        .map((d) => ({
          time: d.date as string,
          value: d.macd_histogram!,
          color:
            d.macd_histogram! >= 0
              ? "rgba(38,166,154,0.5)"
              : "rgba(239,83,80,0.5)",
        }))
    );

    // MACD Line
    const macdLine = chart.addSeries(LineSeries, {
      color: "#2196F3",
      lineWidth: 2,
      priceLineVisible: false,
      lastValueVisible: false,
    });
    macdLine.setData(
      macdData.map((d) => ({ time: d.date as string, value: d.macd_line! }))
    );

    // Signal Line
    const signalLine = chart.addSeries(LineSeries, {
      color: "#FF9800",
      lineWidth: 1,
      priceLineVisible: false,
      lastValueVisible: false,
    });
    signalLine.setData(
      macdData.map((d) => ({
        time: d.date as string,
        value: d.macd_signal!,
      }))
    );

    chart.timeScale().fitContent();

    const observer = new ResizeObserver((entries) => {
      for (const entry of entries) {
        chart.applyOptions({ width: entry.contentRect.width });
      }
    });
    observer.observe(container);

    return () => {
      observer.disconnect();
      chart.remove();
    };
  }, [indicatorData]);

  return (
    <div>
      <h4 className="text-xs font-medium text-muted-foreground mb-1 px-1">
        MACD (12, 26, 9)
        <span className="ml-2 text-[10px]">
          <span className="text-[#2196F3]">MACD</span>
          {" · "}
          <span className="text-[#FF9800]">Signal</span>
        </span>
      </h4>
      <div ref={containerRef} className="rounded-lg overflow-hidden" />
    </div>
  );
}

/**
 * Combined indicator charts: RSI and MACD sub-panes.
 */
export function IndicatorChart({ indicatorData }: IndicatorChartProps) {
  if (indicatorData.length === 0) {
    return (
      <div className="flex items-center justify-center h-40 text-muted-foreground text-sm">
        Không có dữ liệu chỉ báo kỹ thuật
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <RSIChart indicatorData={indicatorData} />
      <MACDChart indicatorData={indicatorData} />
    </div>
  );
}
