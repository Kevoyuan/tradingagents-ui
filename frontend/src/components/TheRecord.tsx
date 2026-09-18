import React, { useMemo } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeSanitize from 'rehype-sanitize';
import { RunEvent, ToolEvidenceItem } from '../types';
import { ToolEvidence } from './ToolEvidence';

interface TheRecordProps {
  events: RunEvent[];
}

function formatTime(isoStr?: string): string {
  if (!isoStr) return '—';
  try {
    const d = new Date(isoStr);
    return d.toTimeString().split(' ')[0] || isoStr;
  } catch {
    return isoStr;
  }
}

function formatAgentName(slug?: string | null): string {
  if (!slug) return 'System';
  return slug
    .split('_')
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(' ');
}

export const TheRecord: React.FC<TheRecordProps> = ({ events }) => {
  // Build a map of call_id -> tool_result for quick lookup
  const toolResultsMap = useMemo(() => {
    const map = new Map<string, RunEvent>();
    for (const e of events) {
      if (e.kind === 'tool_result' && e.payload?.call_id) {
        map.set(e.payload.call_id, e);
      }
    }
    return map;
  }, [events]);

  // Filter out standalone tool_result events if their corresponding tool_call was rendered
  // so we avoid duplicate entries in the visual log
  const toolCallIds = useMemo(() => {
    const set = new Set<string>();
    for (const e of events) {
      if (e.kind === 'tool_call' && e.payload?.call_id) {
        set.add(e.payload.call_id);
      }
    }
    return set;
  }, [events]);

  const displayEvents = useMemo(() => {
    return events.filter((e) => {
      // If this is a tool_result and we already have a tool_call for it, don't duplicate
      if (e.kind === 'tool_result' && e.payload?.call_id && toolCallIds.has(e.payload.call_id)) {
        return false;
      }
      // Keep other events
      return (
        e.kind === 'agent_message' ||
        e.kind === 'tool_call' ||
        e.kind === 'tool_result' ||
        e.kind === 'user_message' ||
        e.kind === 'report_section' ||
        e.kind === 'error' ||
        (e.kind === 'run_state' && (e.payload?.status === 'running' || e.payload?.status === 'completed' || e.payload?.status === 'cancelled'))
      );
    });
  }, [events, toolCallIds]);

  return (
    <div className="py-7.5 pr-12 pb-20 pl-10 border-r border-rule" data-testid="the-record">
      {/* Section Header */}
      <div className="flex items-baseline gap-3.5 pb-2.5 border-b border-ink">
        <h2 className="text-xs font-bold tracking-[0.15em] uppercase text-ink">
          The record
        </h2>
        <span className="ml-auto text-[13px] text-mut tracking-[0.03em] num" data-testid="record-count">
          {events.length} entries · untruncated
        </span>
      </div>

      {/* Record list */}
      <div className="mt-6.5">
        {displayEvents.length === 0 ? (
          <div className="py-8 text-faint text-center text-sm">
            Waiting for run events to stream...
          </div>
        ) : (
          displayEvents.map((evt) => {
            const timeStr = formatTime(evt.ts);
            const agentName = formatAgentName(evt.agent);

            // Agent Message
            if (evt.kind === 'agent_message') {
              const metaTokens = evt.payload?.tokens_in && evt.payload?.tokens_out
                ? `${(evt.payload.tokens_in + evt.payload.tokens_out).toLocaleString()} tok`
                : null;
              const metaLatency = evt.payload?.latency_ms
                ? `${(evt.payload.latency_ms / 1000).toFixed(1)}s`
                : null;
              const metaModel = evt.payload?.model;
              const metaParts = [metaModel, metaTokens, metaLatency].filter(Boolean).join(' · ');

              return (
                <article
                  key={evt.seq}
                  className="py-5 border-b border-rule first:border-t"
                  data-testid={`event-${evt.seq}`}
                >
                  <div className="grid grid-cols-[66px_1fr] gap-5 items-baseline">
                    <span className="text-[12.5px] text-faint tracking-wider num">{timeStr}</span>
                    <div className="flex items-baseline gap-3.5 flex-wrap">
                      <span className="text-[17px] font-semibold tracking-tight text-ink">
                        {agentName}
                      </span>
                      <span className="text-xs font-bold tracking-[0.14em] uppercase text-mut">
                        Agent
                      </span>
                      {metaParts && (
                        <span className="ml-auto text-[12.5px] text-faint num">{metaParts}</span>
                      )}
                    </div>
                  </div>
                  <div className="mt-2.5 pl-[86px] text-[15px] leading-[1.74] text-ink-2 prose prose-sm max-w-none">
                    <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeSanitize]}>
                      {evt.payload?.text || ''}
                    </ReactMarkdown>
                  </div>
                </article>
              );
            }

            // Tool Call / Result Evidence
            if (evt.kind === 'tool_call' || evt.kind === 'tool_result') {
              const callId = evt.payload?.call_id || '';
              const matchedResult = toolResultsMap.get(callId);
              const toolName = evt.payload?.tool || 'unknown_tool';
              const args = evt.payload?.args;
              const ok = matchedResult ? matchedResult.payload?.ok : evt.payload?.ok;
              const durationMs = matchedResult
                ? matchedResult.payload?.duration_ms
                : evt.payload?.duration_ms;
              const result = matchedResult
                ? matchedResult.payload?.result
                : evt.payload?.result;
              const truncated = matchedResult
                ? matchedResult.payload?.truncated
                : evt.payload?.truncated;
              const fullRef = matchedResult
                ? matchedResult.payload?.full_ref
                : evt.payload?.full_ref;

              const evidenceItem: ToolEvidenceItem = {
                tool: toolName,
                call_id: callId,
                args,
                ok,
                duration_ms: durationMs,
                result,
                truncated,
                full_ref: fullRef,
              };

              return (
                <article
                  key={evt.seq}
                  className="py-5 border-b border-rule first:border-t"
                  data-testid={`event-${evt.seq}`}
                >
                  <div className="grid grid-cols-[66px_1fr] gap-5 items-baseline">
                    <span className="text-[12.5px] text-faint tracking-wider num">{timeStr}</span>
                    <div className="flex items-baseline gap-3.5 flex-wrap">
                      <span className="text-[17px] font-semibold tracking-tight text-ink">
                        {agentName}
                      </span>
                      <span className="text-xs font-bold tracking-[0.14em] uppercase text-hold">
                        Tool
                      </span>
                      {durationMs !== undefined && (
                        <span className="ml-auto text-[12.5px] text-faint num">
                          {(durationMs / 1000).toFixed(2)}s
                        </span>
                      )}
                    </div>
                  </div>
                  <ToolEvidence evidence={evidenceItem} />
                </article>
              );
            }

            // User Message
            if (evt.kind === 'user_message') {
              return (
                <article
                  key={evt.seq}
                  className="py-5 border-b border-rule first:border-t"
                  data-testid={`event-${evt.seq}`}
                >
                  <div className="grid grid-cols-[66px_1fr] gap-5 items-baseline">
                    <span className="text-[12.5px] text-faint tracking-wider num">{timeStr}</span>
                    <div className="flex items-baseline gap-3.5 flex-wrap">
                      <span className="text-[17px] font-semibold tracking-tight text-ink">User</span>
                      <span className="text-xs font-bold tracking-[0.14em] uppercase text-mut">
                        Prompt
                      </span>
                    </div>
                  </div>
                  <div className="mt-2.5 pl-[86px] text-[15px] leading-[1.74] text-ink-2">
                    <p>{evt.payload?.text}</p>
                  </div>
                </article>
              );
            }

            // Report Section
            if (evt.kind === 'report_section') {
              return (
                <article
                  key={evt.seq}
                  className="py-5 border-b border-rule first:border-t"
                  data-testid={`event-${evt.seq}`}
                >
                  <div className="grid grid-cols-[66px_1fr] gap-5 items-baseline">
                    <span className="text-[12.5px] text-faint tracking-wider num">{timeStr}</span>
                    <div className="flex items-baseline gap-3.5 flex-wrap">
                      <span className="text-[17px] font-semibold tracking-tight text-ink">
                        {evt.payload?.title || agentName}
                      </span>
                      <span className="text-xs font-bold tracking-[0.14em] uppercase text-mut">
                        Section
                      </span>
                    </div>
                  </div>
                  <div className="mt-2.5 pl-[86px] text-[15px] leading-[1.74] text-ink-2 prose prose-sm max-w-none">
                    <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeSanitize]}>
                      {evt.payload?.markdown || ''}
                    </ReactMarkdown>
                  </div>
                </article>
              );
            }

            // Error
            if (evt.kind === 'error') {
              return (
                <article
                  key={evt.seq}
                  className="py-5 border-b border-rule first:border-t bg-red-50/50"
                  data-testid={`event-${evt.seq}`}
                >
                  <div className="grid grid-cols-[66px_1fr] gap-5 items-baseline">
                    <span className="text-[12.5px] text-sell tracking-wider num">{timeStr}</span>
                    <div className="flex items-baseline gap-3.5 flex-wrap">
                      <span className="text-[17px] font-semibold tracking-tight text-sell">
                        Error
                      </span>
                      <span className="text-xs font-bold tracking-[0.14em] uppercase text-sell">
                        Failure
                      </span>
                    </div>
                  </div>
                  <div className="mt-2.5 pl-[86px] text-[15px] text-sell font-mono">
                    {evt.payload?.message}
                  </div>
                </article>
              );
            }

            // Run State
            if (evt.kind === 'run_state') {
              const status = evt.payload?.status;
              return (
                <article
                  key={evt.seq}
                  className="py-3 border-b border-rule first:border-t bg-page/40"
                  data-testid={`event-${evt.seq}`}
                >
                  <div className="grid grid-cols-[66px_1fr] gap-5 items-baseline">
                    <span className="text-[12.5px] text-faint tracking-wider num">{timeStr}</span>
                    <div className="flex items-baseline gap-3.5 flex-wrap text-xs font-semibold tracking-wider uppercase text-mut">
                      <span>Status: {status}</span>
                    </div>
                  </div>
                </article>
              );
            }

            return null;
          })
        )}
      </div>
    </div>
  );
};
