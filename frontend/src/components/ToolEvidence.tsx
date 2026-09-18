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

  return (
    <div className="my-3 ml-16 border-l border-rule pl-4.5 bg-paper/50">
      {/* Evidence header */}
      <div className="flex items-baseline gap-3 mb-2">
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
        <span className="ml-auto text-xs text-faint num">{durationStr}</span>
      </div>

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

      {(evidence.truncated || evidence.full_ref) && (
        <button
          type="button"
          onClick={handleExpandToggle}
          disabled={isLoadingFull}
          className="mt-2.5 text-xs font-bold tracking-[0.13em] uppercase text-ink cursor-pointer border-b border-ink inline-block pb-0.5 bg-transparent p-0 hover:text-mut hover:border-mut transition-colors"
        >
          {isLoadingFull
            ? 'Loading...'
            : expanded
              ? 'Collapse full result'
              : 'Expand full result'}
        </button>
      )}
    </div>
  );
};
