import React, { useMemo, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeSanitize from 'rehype-sanitize';

import { parseChartData } from '../lib/chartData';
import { DataChart } from './DataChart';

/**
 * Renders an agent message, charting it when it carries a data series.
 *
 * Upstream tool output arrives as prose and the model echoes it verbatim, so
 * these messages are frequently a wall of numbers (a real NET run: 127 CSV
 * rows, then two indicator dumps). When a series can be read completely it is
 * charted and the raw block is collapsed — the same treatment tool output
 * already gets — while the text stays one click away as evidence.
 *
 * The message is left exactly as it was when nothing parses: most messages are
 * ordinary prose.
 */

interface AgentMessageBodyProps {
  text: string;
  /**
   * False for a repeat of a dataset already charted earlier in the record. The
   * text still renders; only the chart is suppressed.
   */
  chartable?: boolean;
}

/**
 * Lines that are raw data rather than commentary, used to size the collapsed
 * view. Covers both shapes: CSV rows (`2026-08-07,300.27,...`) and markdown
 * table rows (`| 2026-08-07 | 300.27 |`).
 */
function countDataLines(text: string): number {
  return text
    .split(/\r?\n/)
    .filter((line) => /\d{4}-\d{2}-\d{2}\s*[,:]/.test(line) || /^\s*\|[^|]*\d{4}-\d{2}-\d{2}/.test(line))
    .length;
}

export const AgentMessageBody: React.FC<AgentMessageBodyProps> = ({ text, chartable = true }) => {
  // Parse regardless of `chartable`: a repeat still needs to be recognised as a
  // dataset so its rows can be collapsed. Only the chart itself is skipped.
  const chart = useMemo(() => parseChartData(text), [text]);
  const [showRaw, setShowRaw] = useState(false);

  const markdown = (
    <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeSanitize]}>{text}</ReactMarkdown>
  );

  if (!chart) {
    return markdown;
  }

  const parts: string[] = [];
  if (chart.bars.length > 0) parts.push(`${chart.bars.length} bars`);
  for (const series of chart.indicators) {
    parts.push(`${series.label} (${series.valueCount} pts)`);
  }

  return (
    <div data-testid={chartable ? 'agent-message-charted' : 'agent-message-repeated'}>
      {chartable ? (
        <>
          <div className="flex items-baseline gap-3 pb-2">
            <span className="text-[11px] font-bold tracking-[0.14em] uppercase text-mut">
              Charted
            </span>
            <span className="text-[12px] text-faint num">{parts.join(' · ')}</span>
          </div>
          <DataChart data={chart} />
        </>
      ) : (
        // The graph re-emits a message as its state grows, so the same dataset
        // can arrive four or five times. Only the first is charted; leaving the
        // repeats as raw prose put a 127-row wall back on screen, which is the
        // problem this feature exists to remove.
        <div
          className="flex items-baseline gap-3 text-[12px] text-faint"
          data-testid="agent-message-repeat"
        >
          <span className="text-[11px] font-bold tracking-[0.14em] uppercase text-mut">
            Repeat
          </span>
          <span className="num">same data as the chart above · {parts.join(' · ')}</span>
        </div>
      )}
      <button
        type="button"
        onClick={() => setShowRaw((value) => !value)}
        aria-expanded={showRaw}
        data-testid="toggle-raw-data"
        className="mt-2 flex items-center gap-2 text-[12px] text-mut hover:text-ink cursor-pointer bg-transparent border-0 p-0"
      >
        <span className="text-[11px] text-faint w-3 shrink-0">{showRaw ? '▾' : '▸'}</span>
        <span>Raw data</span>
        <span className="text-faint num">{countDataLines(text)} rows</span>
      </button>
      {showRaw && <div className="mt-3 text-[15px] leading-[1.74] text-ink-2">{markdown}</div>}
    </div>
  );
};
