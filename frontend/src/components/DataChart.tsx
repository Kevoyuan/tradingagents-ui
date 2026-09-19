import React, { useEffect, useRef, useState } from 'react';
import { CandlestickSeries, LineSeries, createChart, type IChartApi } from 'lightweight-charts';

import type { ParsedChartData } from '../lib/chartData';

/**
 * Chart for series recovered from an agent message.
 *
 * Trades this project's design tokens rather than the library defaults: paper
 * background, hairline gridlines, tabular figures, and — per the mockup rules —
 * exactly one signal colour. That colour is spent on the candlesticks
 * (up/down); indicator overlays stay neutral greys so the recommendation keeps
 * its monopoly on signal.
 *
 * The TradingView attribution logo is left enabled on purpose. The library's
 * licence asks for a link to tradingview.com and states that showing this logo
 * satisfies it; disabling it needs that link to live elsewhere on the page.
 */

interface DataChartProps {
  data: ParsedChartData;
  height?: number;
}

/** Neutral grays for overlays: never a second signal colour. */
const OVERLAY_COLORS = ['#3d3a35', '#6e6a63', '#9c978e'];

export const DataChart: React.FC<DataChartProps> = ({ data, height = 320 }) => {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const [inView, setInView] = useState(false);

  // A long run charts a lot of messages — the NET run had 20 of them, over 9
  // distinct datasets, and the record keeps growing while it streams. Each
  // chart is a live canvas, so only build the ones approaching the viewport.
  // The placeholder keeps the height so nothing shifts when it does mount.
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return undefined;
    if (typeof IntersectionObserver === 'undefined') {
      setInView(true);
      return undefined;
    }
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries.some((entry) => entry.isIntersecting)) {
          setInView(true);
          observer.disconnect();
        }
      },
      { rootMargin: '400px 0px' },
    );
    observer.observe(container);
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    const container = containerRef.current;
    if (!container || !inView) return undefined;

    const chart = createChart(container, {
      autoSize: true,
      layout: {
        background: { color: '#ffffff' },
        textColor: '#6e6a63',
        fontFamily: '"IBM Plex Mono", ui-monospace, SFMono-Regular, Menlo, monospace',
        fontSize: 11,
      },
      grid: {
        vertLines: { color: '#ebe9e4' },
        horzLines: { color: '#ebe9e4' },
      },
      rightPriceScale: { borderColor: '#dcdad4' },
      timeScale: { borderColor: '#dcdad4', fixLeftEdge: true, fixRightEdge: true },
      crosshair: {
        vertLine: { color: '#9c978e', width: 1, style: 3 },
        horzLine: { color: '#9c978e', width: 1, style: 3 },
      },
      handleScale: false,
      handleScroll: false,
    });
    chartRef.current = chart;

    if (data.bars.length > 0) {
      const candles = chart.addSeries(CandlestickSeries, {
        upColor: '#0b6b3a',
        downColor: '#a8121f',
        borderVisible: false,
        wickUpColor: '#0b6b3a',
        wickDownColor: '#a8121f',
        priceLineVisible: false,
      });
      candles.setData(data.bars);
    }

    data.indicators.forEach((series, index) => {
      const line = chart.addSeries(LineSeries, {
        color: OVERLAY_COLORS[index % OVERLAY_COLORS.length],
        lineWidth: 2,
        priceLineVisible: false,
        lastValueVisible: false,
        // Points without a value stay as gaps: bridging a weekend or a holiday
        // would draw a line through a day that has no reading.
        crosshairMarkerVisible: false,
      });
      line.setData(series.points);
    });

    chart.timeScale().fitContent();

    return () => {
      chartRef.current = null;
      chart.remove();
    };
  }, [data, inView]);

  return (
    <div
      ref={containerRef}
      style={{ height }}
      className="w-full border border-rule bg-paper"
      data-testid="data-chart"
    />
  );
};
