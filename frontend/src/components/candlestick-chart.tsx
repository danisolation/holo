"use client";

import { useRef, useEffect, useState, useMemo } from "react";
import {
  createChart,
  CandlestickSeries,
  LineSeries,
  HistogramSeries,
  type IChartApi,
  type ISeriesApi,
  type SeriesType,
} from "lightweight-charts";
import type { PriceData, IndicatorData } from "@/lib/api";
import { Button } from "@/components/ui/button";

const TIME_RANGES = [
  { label: "1T", days: 30 },
  { label: "3T", days: 90 },
  { label: "6T", days: 180 },
  { label: "1N", days: 365 },
  { label: "2N", days: 730 },
] as const;

interface CandlestickChartProps {
  priceData: PriceData[];
  indicatorData?: IndicatorData[];
}

export function CandlestickChart({
  priceData,
  indicatorData,
}: CandlestickChartProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const [selectedRange, setSelectedRange] = useState(365);

  // Filter data by selected time range and ensure ascending sort by date
  const filteredPrices = useMemo(() => {
    if (priceData.length === 0) return [];
    const cutoff = new Date();
    cutoff.setDate(cutoff.getDate() - selectedRange);
    const cutoffStr = cutoff.toISOString().split("T")[0];
    return priceData
      .filter((d) => d.date >= cutoffStr)
      .sort((a, b) => a.date.localeCompare(b.date));
  }, [priceData, selectedRange]);

  const filteredIndicators = useMemo(() => {
    if (!indicatorData || indicatorData.length === 0) return [];
    const cutoff = new Date();
    cutoff.setDate(cutoff.getDate() - selectedRange);
    const cutoffStr = cutoff.toISOString().split("T")[0];
    return indicatorData
      .filter((d) => d.date >= cutoffStr)
      .sort((a, b) => a.date.localeCompare(b.date));
  }, [indicatorData, selectedRange]);

  useEffect(() => {
    const container = containerRef.current;
    if (!container || filteredPrices.length === 0) return;

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
      height: 420,
      crosshair: {
        mode: 0, // Normal
      },
      rightPriceScale: {
        borderColor: "#334155",
      },
      timeScale: {
        borderColor: "#334155",
        timeVisible: false,
      },
    });
    chartRef.current = chart;

    // Candlestick series
    const candleSeries = chart.addSeries(CandlestickSeries, {
      upColor: "#26a69a",
      downColor: "#ef5350",
      borderUpColor: "#26a69a",
      borderDownColor: "#ef5350",
      wickUpColor: "#26a69a",
      wickDownColor: "#ef5350",
    });
    candleSeries.setData(
      filteredPrices.map((d) => ({
        time: d.date as string,
        open: d.open,
        high: d.high,
        low: d.low,
        close: d.close,
      }))
    );

    // Volume histogram
    const volumeSeries = chart.addSeries(HistogramSeries, {
      priceFormat: { type: "volume" },
      priceScaleId: "volume",
    });
    chart.priceScale("volume").applyOptions({
      scaleMargins: { top: 0.8, bottom: 0 },
    });
    volumeSeries.setData(
      filteredPrices.map((d) => ({
        time: d.date as string,
        value: d.volume,
        color: d.close >= d.open ? "rgba(38,166,154,0.3)" : "rgba(239,83,80,0.3)",
      }))
    );

    // MA overlays from indicator data
    if (filteredIndicators.length > 0) {
      // SMA 20 — blue
      const sma20Data = filteredIndicators
        .filter((d) => d.sma_20 != null)
        .map((d) => ({ time: d.date as string, value: d.sma_20! }));
      if (sma20Data.length > 0) {
        const sma20 = chart.addSeries(LineSeries, {
          color: "#2196F3",
          lineWidth: 1,
          priceLineVisible: false,
          lastValueVisible: false,
        });
        sma20.setData(sma20Data);
      }

      // SMA 50 — orange
      const sma50Data = filteredIndicators
        .filter((d) => d.sma_50 != null)
        .map((d) => ({ time: d.date as string, value: d.sma_50! }));
      if (sma50Data.length > 0) {
        const sma50 = chart.addSeries(LineSeries, {
          color: "#FF9800",
          lineWidth: 1,
          priceLineVisible: false,
          lastValueVisible: false,
        });
        sma50.setData(sma50Data);
      }

      // SMA 200 — purple
      const sma200Data = filteredIndicators
        .filter((d) => d.sma_200 != null)
        .map((d) => ({ time: d.date as string, value: d.sma_200! }));
      if (sma200Data.length > 0) {
        const sma200 = chart.addSeries(LineSeries, {
          color: "#9C27B0",
          lineWidth: 1,
          priceLineVisible: false,
          lastValueVisible: false,
        });
        sma200.setData(sma200Data);
      }

      // Bollinger Bands — gray dotted
      const bbUpperData = filteredIndicators
        .filter((d) => d.bb_upper != null)
        .map((d) => ({ time: d.date as string, value: d.bb_upper! }));
      const bbMiddleData = filteredIndicators
        .filter((d) => d.bb_middle != null)
        .map((d) => ({ time: d.date as string, value: d.bb_middle! }));
      const bbLowerData = filteredIndicators
        .filter((d) => d.bb_lower != null)
        .map((d) => ({ time: d.date as string, value: d.bb_lower! }));

      if (bbUpperData.length > 0) {
        const bbUpper = chart.addSeries(LineSeries, {
          color: "rgba(156,163,175,0.5)",
          lineWidth: 1,
          lineStyle: 2, // Dashed
          priceLineVisible: false,
          lastValueVisible: false,
        });
        bbUpper.setData(bbUpperData);
      }
      if (bbMiddleData.length > 0) {
        const bbMid = chart.addSeries(LineSeries, {
          color: "rgba(156,163,175,0.5)",
          lineWidth: 1,
          lineStyle: 2,
          priceLineVisible: false,
          lastValueVisible: false,
        });
        bbMid.setData(bbMiddleData);
      }
      if (bbLowerData.length > 0) {
        const bbLow = chart.addSeries(LineSeries, {
          color: "rgba(156,163,175,0.5)",
          lineWidth: 1,
          lineStyle: 2,
          priceLineVisible: false,
          lastValueVisible: false,
        });
        bbLow.setData(bbLowerData);
      }
    }

    // Fit content
    chart.timeScale().fitContent();

    // ResizeObserver for responsive sizing
    const observer = new ResizeObserver((entries) => {
      for (const entry of entries) {
        const { width } = entry.contentRect;
        chart.applyOptions({ width });
      }
    });
    observer.observe(container);

    return () => {
      observer.disconnect();
      chart.remove();
      chartRef.current = null;
    };
  }, [filteredPrices, filteredIndicators]);

  if (priceData.length === 0) {
    return (
      <div className="flex items-center justify-center h-[420px] bg-[#0f172a] rounded-xl text-muted-foreground">
        Không có dữ liệu giá
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {/* Time range buttons */}
      <div className="flex items-center gap-1">
        <span className="text-xs text-muted-foreground mr-2">Khoảng thời gian:</span>
        {TIME_RANGES.map((range) => (
          <Button
            key={range.days}
            variant={selectedRange === range.days ? "default" : "outline"}
            size="xs"
            onClick={() => setSelectedRange(range.days)}
          >
            {range.label}
          </Button>
        ))}
      </div>

      {/* MA Legend */}
      <div className="flex items-center gap-4 text-xs">
        <span className="flex items-center gap-1">
          <span className="inline-block w-3 h-0.5 bg-[#2196F3]" /> SMA 20
        </span>
        <span className="flex items-center gap-1">
          <span className="inline-block w-3 h-0.5 bg-[#FF9800]" /> SMA 50
        </span>
        <span className="flex items-center gap-1">
          <span className="inline-block w-3 h-0.5 bg-[#9C27B0]" /> SMA 200
        </span>
        <span className="flex items-center gap-1">
          <span className="inline-block w-3 h-0.5 bg-gray-400 opacity-50" style={{ borderTop: "1px dashed" }} /> BB
        </span>
      </div>

      {/* Chart container */}
      <div ref={containerRef} className="rounded-xl overflow-hidden" />
    </div>
  );
}
