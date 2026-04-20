"use client";

import { useRef, useEffect } from "react";
import {
  createChart,
  LineSeries,
  HistogramSeries,
  type IChartApi,
} from "lightweight-charts";
import type { IndicatorData } from "@/lib/api";
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";

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

  return <div ref={containerRef} className="rounded-lg overflow-hidden" />;
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

  return <div ref={containerRef} className="rounded-lg overflow-hidden" />;
}

/**
 * ATR sub-chart: ATR(14) line showing price volatility.
 */
function ATRChart({ indicatorData }: { indicatorData: IndicatorData[] }) {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const atrData = indicatorData
      .filter((d) => d.atr_14 != null)
      .map((d) => ({ time: d.date as string, value: d.atr_14! }))
      .sort((a, b) => (a.time as string).localeCompare(b.time as string));

    if (atrData.length === 0) return;

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

    const atrSeries = chart.addSeries(LineSeries, {
      color: "#FBBF24",
      lineWidth: 2,
      priceLineVisible: false,
      lastValueVisible: true,
    });
    atrSeries.setData(atrData);

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

  return <div ref={containerRef} className="rounded-lg overflow-hidden" />;
}

/**
 * ADX sub-chart: ADX line + +DI + -DI with reference line at 25.
 */
function ADXChart({ indicatorData }: { indicatorData: IndicatorData[] }) {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const adxData = indicatorData
      .filter(
        (d) => d.adx_14 != null && d.plus_di_14 != null && d.minus_di_14 != null
      )
      .sort((a, b) => a.date.localeCompare(b.date));

    if (adxData.length === 0) return;

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

    // ADX line (cyan, primary)
    const adxLine = chart.addSeries(LineSeries, {
      color: "#06B6D4",
      lineWidth: 2,
      priceLineVisible: false,
      lastValueVisible: true,
    });
    adxLine.setData(
      adxData.map((d) => ({ time: d.date as string, value: d.adx_14! }))
    );

    // +DI line (green)
    const posLine = chart.addSeries(LineSeries, {
      color: "#22C55E",
      lineWidth: 1,
      priceLineVisible: false,
      lastValueVisible: false,
    });
    posLine.setData(
      adxData.map((d) => ({ time: d.date as string, value: d.plus_di_14! }))
    );

    // -DI line (red)
    const negLine = chart.addSeries(LineSeries, {
      color: "#EF4444",
      lineWidth: 1,
      priceLineVisible: false,
      lastValueVisible: false,
    });
    negLine.setData(
      adxData.map((d) => ({ time: d.date as string, value: d.minus_di_14! }))
    );

    // Reference line at 25 (strong trend threshold)
    const refLine = chart.addSeries(LineSeries, {
      color: "rgba(255,255,255,0.25)",
      lineWidth: 1,
      lineStyle: 2,
      priceLineVisible: false,
      lastValueVisible: false,
    });
    refLine.setData(
      adxData.map((d) => ({ time: d.date as string, value: 25 }))
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

  return <div ref={containerRef} className="rounded-lg overflow-hidden" />;
}

/**
 * Stochastic sub-chart: %K and %D lines with 80/20 overbought/oversold zones.
 */
function StochasticChart({
  indicatorData,
}: {
  indicatorData: IndicatorData[];
}) {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const stochData = indicatorData
      .filter((d) => d.stoch_k_14 != null && d.stoch_d_14 != null)
      .sort((a, b) => a.date.localeCompare(b.date));

    if (stochData.length === 0) return;

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

    // %K line (pink, primary)
    const kLine = chart.addSeries(LineSeries, {
      color: "#EC4899",
      lineWidth: 2,
      priceLineVisible: false,
      lastValueVisible: true,
    });
    kLine.setData(
      stochData.map((d) => ({ time: d.date as string, value: d.stoch_k_14! }))
    );

    // %D line (indigo, signal)
    const dLine = chart.addSeries(LineSeries, {
      color: "#818CF8",
      lineWidth: 1,
      priceLineVisible: false,
      lastValueVisible: false,
    });
    dLine.setData(
      stochData.map((d) => ({ time: d.date as string, value: d.stoch_d_14! }))
    );

    // Overbought line (80)
    const overbought = chart.addSeries(LineSeries, {
      color: "rgba(239,83,80,0.4)",
      lineWidth: 1,
      lineStyle: 2,
      priceLineVisible: false,
      lastValueVisible: false,
    });
    overbought.setData(
      stochData.map((d) => ({ time: d.date as string, value: 80 }))
    );

    // Oversold line (20)
    const oversold = chart.addSeries(LineSeries, {
      color: "rgba(38,166,154,0.4)",
      lineWidth: 1,
      lineStyle: 2,
      priceLineVisible: false,
      lastValueVisible: false,
    });
    oversold.setData(
      stochData.map((d) => ({ time: d.date as string, value: 20 }))
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

  return <div ref={containerRef} className="rounded-lg overflow-hidden" />;
}

/**
 * Combined indicator charts: all 5 sub-panes in collapsible accordion.
 * RSI and MACD expanded by default (existing behavior).
 * ATR, ADX, Stochastic collapsed by default (new, opt-in).
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
    <Accordion multiple defaultValue={["rsi", "macd"]}>
      <AccordionItem value="rsi">
        <AccordionTrigger className="text-xs font-medium text-muted-foreground px-1 py-2">
          RSI (14)
          <span className="ml-2 text-[10px]">
            <span className="text-[#ef5350]">70 quá mua</span>
            {" · "}
            <span className="text-[#26a69a]">30 quá bán</span>
          </span>
        </AccordionTrigger>
        <AccordionContent>
          <RSIChart indicatorData={indicatorData} />
        </AccordionContent>
      </AccordionItem>

      <AccordionItem value="macd">
        <AccordionTrigger className="text-xs font-medium text-muted-foreground px-1 py-2">
          MACD (12, 26, 9)
          <span className="ml-2 text-[10px]">
            <span className="text-[#2196F3]">MACD</span>
            {" · "}
            <span className="text-[#FF9800]">Signal</span>
          </span>
        </AccordionTrigger>
        <AccordionContent>
          <MACDChart indicatorData={indicatorData} />
        </AccordionContent>
      </AccordionItem>

      <AccordionItem value="atr">
        <AccordionTrigger className="text-xs font-medium text-muted-foreground px-1 py-2">
          ATR (14)
          <span className="ml-2 text-[10px]">
            <span className="text-[#FBBF24]">Biến động giá</span>
          </span>
        </AccordionTrigger>
        <AccordionContent>
          <ATRChart indicatorData={indicatorData} />
        </AccordionContent>
      </AccordionItem>

      <AccordionItem value="adx">
        <AccordionTrigger className="text-xs font-medium text-muted-foreground px-1 py-2">
          ADX (14)
          <span className="ml-2 text-[10px]">
            <span className="text-[#06B6D4]">ADX</span>
            {" · "}
            <span className="text-[#22C55E]">+DI</span>
            {" · "}
            <span className="text-[#EF4444]">-DI</span>
          </span>
        </AccordionTrigger>
        <AccordionContent>
          <ADXChart indicatorData={indicatorData} />
        </AccordionContent>
      </AccordionItem>

      <AccordionItem value="stochastic">
        <AccordionTrigger className="text-xs font-medium text-muted-foreground px-1 py-2">
          Stochastic (14, 3)
          <span className="ml-2 text-[10px]">
            <span className="text-[#EC4899]">%K</span>
            {" · "}
            <span className="text-[#818CF8]">%D</span>
          </span>
        </AccordionTrigger>
        <AccordionContent>
          <StochasticChart indicatorData={indicatorData} />
        </AccordionContent>
      </AccordionItem>
    </Accordion>
  );
}
