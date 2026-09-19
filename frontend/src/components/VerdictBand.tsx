import React from 'react';
import { RunStatus, Verdict } from '../types';

interface VerdictBandProps {
  verdict: Verdict | null;
  runStatus: RunStatus | undefined;
  activeAgent: string | null;
  activeActivity: string | null;
  agentsDone: number;
  totalAgents: number;
  reportsDone: number;
  totalReports: number;
  elapsedFormatted: string;
}

export const VerdictBand: React.FC<VerdictBandProps> = ({
  verdict,
  runStatus,
  activeAgent,
  activeActivity,
  agentsDone,
  totalAgents,
  reportsDone,
  totalReports,
  elapsedFormatted,
}) => {
  // Determine verdict rating and colors
  let ratingText = verdict?.rating || (runStatus === 'completed' ? 'HOLD' : 'ANALYZING');
  let signalColor = 'var(--faint)';
  let convictionMarker = '';

  if (verdict?.rating) {
    switch (verdict.rating) {
      case 'Buy':
        signalColor = 'var(--buy)';
        convictionMarker = '● High Conviction';
        break;
      case 'Overweight':
        signalColor = 'var(--buy)';
        convictionMarker = '▲ Moderate Conviction';
        break;
      case 'Hold':
        signalColor = 'var(--hold)';
        convictionMarker = '■ Neutral';
        break;
      case 'Underweight':
        signalColor = 'var(--sell)';
        convictionMarker = '▼ Moderate Conviction';
        break;
      case 'Sell':
        signalColor = 'var(--sell)';
        convictionMarker = '● High Conviction';
        break;
    }
  } else if (runStatus === 'cancelled') {
    ratingText = 'CANCELLED';
    signalColor = 'var(--faint)';
  } else if (runStatus === 'failed') {
    ratingText = 'FAILED';
    signalColor = 'var(--sell)';
  }

  // Source section caption
  const sourceCaption = verdict?.source_section
    ? verdict.source_section === 'portfolio'
      ? 'Portfolio Manager Decision'
      : 'Trader Plan · Initial Proposal'
    : runStatus === 'running' || runStatus === 'pending'
      ? 'Analysis In Progress'
      : runStatus === 'cancelled'
        ? 'Run Cancelled by User'
        : runStatus === 'failed'
          ? 'Run Failed'
          : 'Awaiting Run Initiation';

  const entryPrice = verdict?.entry_price || '—';
  const stopLoss = verdict?.stop_loss || '—';
  const positionSizing = verdict?.position_sizing || '—';
  const summary =
    verdict?.executive_summary ||
    (verdict?.price_target ? `Price Target: ${verdict.price_target}` : null) ||
    'Multi-agent financial analysis pipeline evaluating real-time indicators and risk parameters.';

  const nowText = activeAgent
    ? `${activeAgent} · ${activeActivity || 'evaluating signals'}`
    : runStatus === 'completed'
      ? 'All agents finished · Report complete'
      : runStatus === 'cancelled'
        ? 'Run stopped'
        : runStatus === 'failed'
          ? 'Run stopped before finishing'
          : 'Standby';

  return (
    <section
      className="sticky top-[62px] z-20 border-b border-ink bg-paper select-none"
      data-testid="verdict-band"
    >
      <div className="grid grid-cols-[auto_1px_auto_1px_1fr] items-stretch px-10">
        {/* Left: Action keyword */}
        <div className="py-[22px] pr-11 pb-6">
          <div className="cap text-mut flex items-center gap-2.5">
            <i
              className="w-1.5 h-1.5 block shrink-0"
              style={{ backgroundColor: signalColor }}
              aria-hidden="true"
            />
            <span>{sourceCaption}</span>
          </div>

          <div
            className="text-[76px] font-semibold tracking-[-0.045em] leading-[0.92] mt-2.5 uppercase"
            style={{ color: signalColor }}
            data-testid="verdict-action"
          >
            {ratingText.toUpperCase()}
          </div>

          {convictionMarker && (
            <div
              className="mt-1.5 text-xs font-semibold tracking-wider uppercase"
              style={{ color: signalColor }}
            >
              {convictionMarker}
            </div>
          )}
        </div>

        {/* Vertical divider */}
        <div className="bg-rule w-[1px]" />

        {/* Middle: Key figures */}
        <div className="py-6 px-11 flex flex-col justify-center gap-4">
          <div className="flex gap-11">
            <div>
              <div className="text-xs font-semibold tracking-[0.12em] uppercase text-faint">
                Entry price
              </div>
              <div className="text-[26px] font-semibold tracking-[-0.025em] mt-1 text-ink num">
                {entryPrice}
              </div>
            </div>
            <div>
              <div className="text-xs font-semibold tracking-[0.12em] uppercase text-faint">
                Stop loss
              </div>
              <div className="text-[26px] font-semibold tracking-[-0.025em] mt-1 text-ink num">
                {stopLoss}
              </div>
            </div>
            <div>
              <div className="text-xs font-semibold tracking-[0.12em] uppercase text-faint">
                Position sizing
              </div>
              <div className="text-[26px] font-semibold tracking-[-0.025em] mt-1 text-ink num">
                {positionSizing}
              </div>
            </div>
          </div>
          <p className="text-[13.5px] text-mut leading-normal max-w-[34ch] truncate-2-lines">
            {summary}
          </p>
        </div>

        {/* Vertical divider */}
        <div className="bg-rule w-[1px]" />

        {/* Right: Now & Progress */}
        <div className="py-6 pl-11 flex flex-col justify-center gap-3.5">
          <div className="flex items-baseline gap-3">
            <span className="text-xs font-semibold tracking-[0.12em] uppercase text-faint">
              Now
            </span>
            <span className="text-[15px] font-semibold text-ink" data-testid="active-agent-now">
              {nowText}
            </span>
          </div>

          <div className="flex gap-7">
            <div>
              <div className="text-xs font-semibold tracking-[0.12em] uppercase text-faint">
                Agents
              </div>
              <div className="text-[17px] font-semibold mt-1 text-ink num">
                {agentsDone} / {totalAgents}
              </div>
            </div>
            <div>
              <div className="text-xs font-semibold tracking-[0.12em] uppercase text-faint">
                Reports
              </div>
              <div className="text-[17px] font-semibold mt-1 text-ink num">
                {reportsDone} / {totalReports}
              </div>
            </div>
            <div>
              <div className="text-xs font-semibold tracking-[0.12em] uppercase text-faint">
                Elapsed
              </div>
              <div className="text-[17px] font-semibold mt-1 text-ink num">
                {elapsedFormatted}
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};
