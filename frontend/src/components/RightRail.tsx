import React, { useMemo } from 'react';
import { AgentInfo, RunHeader, RunStats } from '../types';

interface RightRailProps {
  agents: AgentInfo[];
  stats: RunStats | null | undefined;
  header: RunHeader | null;
  reportsDone: number;
  totalReports: number;
  elapsedFormatted: string;
  tokenHistory?: { elapsedSec: number; tokensIn: number; tokensOut: number }[];
}

function formatTokens(count?: number): string {
  if (count === undefined || count === null || count === 0) return '0';
  if (count >= 1_000_000) return `${(count / 1_000_000).toFixed(1)}M`;
  if (count >= 1_000) return `${(count / 1_000).toFixed(1)}k`;
  return count.toString();
}

function formatCost(costUsd?: number | null): string {
  if (costUsd === undefined || costUsd === null) return '$0.000';
  return `$${costUsd.toFixed(3)}`;
}

export const RightRail: React.FC<RightRailProps> = ({
  agents,
  stats,
  header,
  reportsDone,
  totalReports,
  elapsedFormatted,
  tokenHistory = [],
}) => {
  const activeCount = agents.filter((a) => a.status === 'done').length;
  const totalAgents = agents.length;

  // Group agents by team
  const teams = useMemo(() => {
    const map = [
      { key: 'analyst', title: 'Analyst Team' },
      { key: 'research', title: 'Research Team' },
      { key: 'trading', title: 'Trading Team' },
      { key: 'risk', title: 'Risk Management' },
      { key: 'portfolio', title: 'Portfolio' },
    ];

    return map.map((t) => {
      const teamAgents = agents.filter((a) => a.team === t.key);
      const done = teamAgents.filter((a) => a.status === 'done').length;
      return {
        ...t,
        agents: teamAgents,
        done,
        total: teamAgents.length,
      };
    });
  }, [agents]);

  const totalTokens = (stats?.tokens_in || 0) + (stats?.tokens_out || 0);

  // Generate SVG points for token burn sparkline
  const chartPoints = useMemo(() => {
    const width = 364;
    const baselineY = 96;

    if (!tokenHistory || tokenHistory.length < 2) {
      // Default static/subtle line
      return {
        polyPoints: '0,92 364,92',
        fillPoints: '0,92 364,92 364,96 0,96',
        outPoints: '0,95 364,95',
      };
    }

    const maxTime = Math.max(...tokenHistory.map((h) => h.elapsedSec), 1);
    const maxTokens = Math.max(...tokenHistory.map((h) => h.tokensIn + h.tokensOut), 100);

    const inCoords = tokenHistory.map((h) => {
      const x = Math.round((h.elapsedSec / maxTime) * width);
      const ratio = (h.tokensIn + h.tokensOut) / maxTokens;
      const y = Math.round(baselineY - ratio * 66);
      return `${x},${y}`;
    });

    const outCoords = tokenHistory.map((h) => {
      const x = Math.round((h.elapsedSec / maxTime) * width);
      const ratio = h.tokensOut / maxTokens;
      const y = Math.round(baselineY - ratio * 66);
      return `${x},${y}`;
    });

    return {
      polyPoints: inCoords.join(' '),
      fillPoints: `0,${baselineY} ${inCoords.join(' ')} ${width},${baselineY}`,
      outPoints: outCoords.join(' '),
    };
  }, [tokenHistory]);

  return (
    <aside className="py-7.5 px-8 pb-20 bg-page select-none flex flex-col gap-7.5" data-testid="right-rail">
      {/* 1. Who is speaking */}
      <section>
        <div className="flex items-baseline gap-3.5 pb-2.5 border-b border-ink">
          <h2 className="text-xs font-bold tracking-[0.15em] uppercase text-ink">
            Who is speaking
          </h2>
          <span className="ml-auto text-[13px] text-mut tracking-[0.03em] num" data-testid="roster-count">
            {activeCount} / {totalAgents}
          </span>
        </div>

        <div className="mt-3.5 space-y-4">
          {teams.map((t) => (
            <div key={t.key} className="space-y-1">
              <div className="text-xs font-bold tracking-[0.14em] uppercase text-faint pb-1.5 border-b border-rule flex justify-between">
                <span>{t.title}</span>
                <span className="num font-semibold">
                  {t.done} / {t.total}
                </span>
              </div>
              <ul className="list-none m-0 p-0">
                {t.agents.map((ag) => {
                  let mkClass = 'border border-faint bg-transparent';
                  let nmClass = 'text-[14.5px] text-faint';
                  let rightText = 'queued';

                  if (ag.status === 'done') {
                    mkClass = 'bg-faint border-faint';
                    nmClass = 'text-[14.5px] text-ink-2';
                    rightText = ag.tokens > 0 ? `${formatTokens(ag.tokens)}` : 'done';
                  } else if (ag.status === 'running') {
                    mkClass = 'bg-ink border-ink';
                    nmClass = 'text-[14.5px] font-bold text-ink';
                    rightText = 'running';
                  }

                  return (
                    <li
                      key={ag.slug}
                      className="grid grid-cols-[18px_1fr_auto] gap-3 items-baseline py-1.5 border-b border-rule-2 last:border-b-0"
                      data-testid={`agent-item-${ag.slug}`}
                    >
                      <span
                        className={`w-[9px] h-[9px] self-center shrink-0 ${mkClass}`}
                        aria-hidden="true"
                      />
                      <span className={nmClass}>{ag.name}</span>
                      <span className="text-[12.5px] text-faint num">{rightText}</span>
                    </li>
                  );
                })}
              </ul>
            </div>
          ))}
        </div>
      </section>

      {/* 2. Token burn */}
      <section className="burn">
        <div className="flex items-baseline gap-3.5 pb-2.5 border-b border-ink">
          <h2 className="text-xs font-bold tracking-[0.15em] uppercase text-ink">
            Token burn
          </h2>
          <span className="ml-auto text-[13px] text-mut tracking-[0.03em]">
            by elapsed time
          </span>
        </div>

        <div className="mt-4">
          <div className="flex items-baseline gap-2.5 mb-2.5">
            <span className="text-[30px] font-semibold tracking-tight text-ink num">
              {formatTokens(totalTokens)}
            </span>
            <span className="text-[13px] text-mut">tokens</span>

            <div className="ml-auto text-right">
              <span className="text-xs font-semibold tracking-[0.12em] uppercase text-faint block">
                Est. cost
              </span>
              <div className="text-[22px] font-semibold tracking-tight text-ink num">
                {formatCost(stats?.cost_usd)}
              </div>
            </div>
          </div>

          <svg
            width="100%"
            height="118"
            viewBox="0 0 364 118"
            preserveAspectRatio="none"
            role="img"
            aria-label="Token burn across elapsed time"
          >
            <line x1="0" y1="96" x2="364" y2="96" stroke="#dcdad4" />
            <line x1="0" y1="62" x2="364" y2="62" stroke="#ebe9e4" />
            <line x1="0" y1="28" x2="364" y2="28" stroke="#ebe9e4" />

            <polygon fill="rgba(10,10,10,.10)" points={chartPoints.fillPoints} />
            <polyline
              fill="none"
              stroke="#0a0a0a"
              strokeWidth="1.6"
              points={chartPoints.polyPoints}
            />
            <polyline
              fill="none"
              stroke="#9c978e"
              strokeWidth="1.4"
              strokeDasharray="4 3"
              points={chartPoints.outPoints}
            />

            <line x1="109" y1="0" x2="109" y2="96" stroke="#dcdad4" strokeDasharray="2 3" />
            <line x1="218" y1="0" x2="218" y2="96" stroke="#dcdad4" strokeDasharray="2 3" />
            <line x1="291" y1="0" x2="291" y2="96" stroke="#dcdad4" strokeDasharray="2 3" />
          </svg>

          <div className="flex justify-between text-xs text-faint mt-1.5 num">
            <span>00:00</span>
            <span>{elapsedFormatted}</span>
          </div>

          <div className="flex gap-5 mt-3 text-[12.5px] text-mut">
            <span className="flex items-center gap-2">
              <i className="w-4 h-0.5 block bg-ink" />
              input {formatTokens(stats?.tokens_in || 0)}
            </span>
            <span className="flex items-center gap-2">
              <i className="w-4 h-0.5 block bg-faint" />
              output {formatTokens(stats?.tokens_out || 0)}
            </span>
          </div>
        </div>
      </section>

      {/* 3. Run stats */}
      <section>
        <div className="flex items-baseline gap-3.5 pb-2.5 border-b border-ink">
          <h2 className="text-xs font-bold tracking-[0.15em] uppercase text-ink">
            Run stats
          </h2>
          <span className="ml-auto text-[13px] text-mut tracking-[0.03em]">
            {header?.config?.quick_model || 'standard_run'}
          </span>
        </div>

        <div className="grid grid-cols-2 border-t border-l border-rule mt-3.5 bg-paper">
          <div className="border-r border-b border-rule p-3">
            <div className="text-xs font-bold tracking-[0.12em] uppercase text-faint">
              LLM calls
            </div>
            <div className="text-[19px] font-semibold tracking-tight mt-0.5 text-ink num">
              {stats?.llm_calls || 0}
            </div>
          </div>
          <div className="border-r border-b border-rule p-3">
            <div className="text-xs font-bold tracking-[0.12em] uppercase text-faint">
              Tool calls
            </div>
            <div className="text-[19px] font-semibold tracking-tight mt-0.5 text-ink num">
              {stats?.tool_calls || 0}
            </div>
          </div>
          <div className="border-r border-b border-rule p-3">
            <div className="text-xs font-bold tracking-[0.12em] uppercase text-faint">
              Tokens in
            </div>
            <div className="text-[19px] font-semibold tracking-tight mt-0.5 text-ink num">
              {formatTokens(stats?.tokens_in || 0)}
            </div>
          </div>
          <div className="border-r border-b border-rule p-3">
            <div className="text-xs font-bold tracking-[0.12em] uppercase text-faint">
              Tokens out
            </div>
            <div className="text-[19px] font-semibold tracking-tight mt-0.5 text-ink num">
              {formatTokens(stats?.tokens_out || 0)}
            </div>
          </div>
          <div className="border-r border-b border-rule p-3">
            <div className="text-xs font-bold tracking-[0.12em] uppercase text-faint">
              Reports
            </div>
            <div className="text-[19px] font-semibold tracking-tight mt-0.5 text-ink num">
              {reportsDone} / {totalReports}
            </div>
          </div>
          <div className="border-r border-b border-rule p-3">
            <div className="text-xs font-bold tracking-[0.12em] uppercase text-faint">
              Elapsed
            </div>
            <div className="text-[19px] font-semibold tracking-tight mt-0.5 text-ink num">
              {elapsedFormatted}
            </div>
          </div>
        </div>
      </section>

      {/* Footnote */}
      <p className="text-[12.5px] leading-relaxed text-faint border-t border-rule pt-3 mt-1">
        Refreshing this page does not interrupt the run. Reopening reconnects to the live
        stream and backfills anything missed.
      </p>
    </aside>
  );
};
