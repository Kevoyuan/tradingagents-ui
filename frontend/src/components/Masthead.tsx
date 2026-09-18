import React from 'react';
import { RunHeader } from '../types';

interface MastheadProps {
  header: RunHeader | null;
  elapsedFormatted: string;
  onStop: () => void;
  onNewRun: () => void;
}

export const Masthead: React.FC<MastheadProps> = ({
  header,
  elapsedFormatted,
  onStop,
  onNewRun,
}) => {
  const isRunning = header?.status === 'running' || header?.status === 'pending';
  const ticker = header?.ticker || '—';
  const tradeDate = header?.trade_date || '—';
  const runId = header?.run_id ? `RUN ${header.run_id.slice(0, 8).toUpperCase()}` : 'NO ACTIVE RUN';

  return (
    <header className="h-[62px] flex items-center gap-6 px-10 border-b border-ink bg-paper select-none sticky top-0 z-30">
      {/* Wordmark */}
      <span className="text-[13px] font-bold tracking-[0.15em] uppercase text-ink">
        TradingAgents
      </span>

      {/* Nav */}
      <nav className="flex gap-5" aria-label="Main Navigation">
        <a
          href="#"
          aria-current="page"
          className="text-xs font-bold tracking-[0.13em] uppercase text-ink no-underline"
        >
          Monitor
        </a>
        <a
          href="#"
          className="text-xs font-medium tracking-[0.13em] uppercase text-faint no-underline hover:text-ink transition-colors"
        >
          Reports
        </a>
        <a
          href="#"
          className="text-xs font-medium tracking-[0.13em] uppercase text-faint no-underline hover:text-ink transition-colors"
        >
          Settings
        </a>
      </nav>

      {/* Right controls */}
      <div className="ml-auto flex items-center gap-6">
        <div className="text-right">
          <div className="text-lg font-semibold tracking-tight leading-tight text-ink">
            {ticker}
          </div>
          <div className="text-xs text-mut tracking-[0.06em]">
            {tradeDate} · {runId}
          </div>
        </div>

        <div className="text-xl font-semibold tracking-tight text-ink num">
          {elapsedFormatted}
        </div>

        {isRunning ? (
          <button
            type="button"
            onClick={onStop}
            className="sbtn font-grotesk text-xs font-semibold tracking-[0.13em] uppercase bg-transparent border border-ink text-ink py-2.5 px-4.5 cursor-pointer hover:bg-ink hover:text-paper transition-colors"
            data-testid="stop-run-button"
          >
            Stop run
          </button>
        ) : (
          <button
            type="button"
            onClick={onNewRun}
            className="sbtn font-grotesk text-xs font-semibold tracking-[0.13em] uppercase bg-transparent border border-ink text-ink py-2.5 px-4.5 cursor-pointer hover:bg-ink hover:text-paper transition-colors"
            data-testid="new-run-button"
          >
            New run
          </button>
        )}
      </div>
    </header>
  );
};
