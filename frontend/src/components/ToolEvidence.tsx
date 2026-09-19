import React, { useState } from 'react';
import { ToolEvidenceItem } from '../types';

interface ToolEvidenceProps {
  evidence: ToolEvidenceItem;
}

export const ToolEvidence: React.FC<ToolEvidenceProps> = ({ evidence }) => {
  const [expanded, setExpanded] = useState<boolean>(false);
  const [fullContent, setFullContent] = useState<string | null>(null);
  const [isLoadingFull, setIsLoadingFull] = useState<boolean>(false);

  const durationStr = evidence.duration_ms !== undefined ? `${(evidence.duration_ms / 1000).toFixed(2)}s` : '—';
  const argsFormatted =
    typeof evidence.args === 'string'
      ? evidence.args
      : evidence.args
        ? JSON.stringify(evidence.args, null, 2)
        : '—';

  const handleExpandToggle = async () => {
    if (expanded) {
      setExpanded(false);
      return;
    }

    if (evidence.full_ref && !fullContent) {
      setIsLoadingFull(true);
      try {
        const res = await fetch(evidence.full_ref);
        if (res.ok) {
          const text = await res.text();
          setFullContent(text);
        }
      } catch (err) {
        console.error('Failed to fetch full tool result', err);
      } finally {
        setIsLoadingFull(false);
      }
    }
    setExpanded(true);
  };

  const displayResult = expanded
    ? fullContent || evidence.result || 'No output'
    : evidence.result || 'No output';

  // One line per tool call by default. Raw tool output is often hundreds of
  // rows of CSV, and rendering it inline for every call buried the reasoning
  // the user actually reads. Collapsed state shows what the call was and how
  // much came back; the detail is one click away.
  const rawResult = evidence.result || '';
  const resultLines = rawResult ? rawResult.split('\n').filter((l) => l.trim()).length : 0;
  const firstLine = rawResult.split('\n').find((l) => l.trim())?.trim() ?? '';
  const summary =
    resultLines > 3
      ? `${resultLines} rows`
      : firstLine.length > 78
        ? `${firstLine.slice(0, 78)}…`
        : firstLine || 'no output';

  return (
    <div className="my-3 ml-16 border-l border-rule pl-4.5 bg-paper/50">
      {/* Evidence header - also the disclosure control */}
      <button
        type="button"
        onClick={handleExpandToggle}
        aria-expanded={expanded}
        className="flex w-full items-baseline gap-3 text-left bg-transparent border-0 p-0 cursor-pointer group"
        data-testid={`tool-evidence-${evidence.tool}`}
      >
        <span className="text-[11px] text-faint w-3 shrink-0">{expanded ? '▾' : '▸'}</span>
        <span className="font-mono text-[13px] font-medium text-ink">
          {evidence.tool}
        </span>
        {evidence.ok !== undefined && (
          <span
            className={`text-xs font-bold tracking-[0.13em] uppercase ${
              evidence.ok ? 'text-buy' : 'text-sell'
            }`}
          >
            {evidence.ok ? 'ok' : 'err'}
          </span>
        )}
        {!expanded && (
          <span className="text-xs text-mut truncate min-w-0" data-testid="tool-evidence-summary">
            {summary}
          </span>
        )}
        <span className="ml-auto text-xs text-faint num">{durationStr}</span>
      </button>

      {expanded && (
      <div className="mt-2">
      {/* IO description list */}
      <dl className="grid grid-cols-[50px_1fr] gap-x-4 gap-y-1.5 text-xs my-0">
        <dt className="text-xs font-bold tracking-[0.12em] uppercase text-faint pt-0.5">
          args
        </dt>
        <dd className="font-mono text-[12.5px] leading-relaxed text-ink-2 break-all m-0">
          {argsFormatted}
        </dd>

        <dt className="text-xs font-bold tracking-[0.12em] uppercase text-faint pt-0.5">
          result
        </dt>
        <dd className="font-mono text-[12.5px] leading-relaxed text-ink-2 break-all m-0">
          <pre className="font-mono text-[12.5px] leading-relaxed text-ink-2 whitespace-pre-wrap break-all m-0">
            {displayResult}
          </pre>
        </dd>
      </dl>

      {evidence.truncated && (
        <p className="mt-2 text-xs text-faint">
          {isLoadingFull ? 'Loading full result…' : 'Showing the preview; the full result loads on expand.'}
        </p>
      )}
      </div>
      )}
    </div>
  );
};
