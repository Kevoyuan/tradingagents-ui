import React from 'react';
import { Verdict } from '../types';

interface ReportVerdictCardProps {
  verdict: Verdict | null;
  ticker: string;
  tradeDate: string;
}

export const ReportVerdictCard: React.FC<ReportVerdictCardProps> = ({
  verdict,
  ticker,
  tradeDate,
}) => {
  const rating = verdict?.rating;

  // Determine signal color per Section 7:
  // Buy/Overweight -> green (text-buy, bg-buy)
  // Hold -> neutral grey (text-hold, bg-hold)
  // Underweight/Sell -> red (text-sell, bg-sell)
  let actionColorClass = 'text-hold';
  let dotBgClass = 'bg-hold';
  if (rating === 'Buy' || rating === 'Overweight') {
    actionColorClass = 'text-buy';
    dotBgClass = 'bg-buy';
  } else if (rating === 'Underweight' || rating === 'Sell') {
    actionColorClass = 'text-sell';
    dotBgClass = 'bg-sell';
  }

  const sourceLabel =
    verdict?.source_section === 'portfolio'
      ? 'Portfolio Manager Decision'
      : verdict?.source_section === 'trader'
      ? 'Trading Team Plan'
      : 'Automated Synthesis';

  return (
    <section
      className="border-b border-ink bg-paper select-none"
      data-testid="verdict-card"
      aria-label="Report Verdict"
    >
      <div className="grid grid-cols-1 md:grid-cols-[auto_1px_1fr] items-stretch px-10">
        {/* Left column: display-scale recommendation action */}
        <div className="py-6 pr-10">
          <div className="text-xs font-semibold tracking-[0.13em] uppercase text-mut flex items-center gap-2">
            <i className={`w-2 h-2 ${dotBgClass} block shrink-0`} aria-hidden="true"></i>
            <span>VERDICT · {sourceLabel}</span>
          </div>

          <div
            className={`text-6xl md:text-7xl font-semibold tracking-[-0.045em] leading-none mt-3.5 uppercase ${actionColorClass}`}
            data-testid="verdict-action"
          >
            {rating || 'NO VERDICT'}
          </div>

          <div className="mt-2 text-xs text-mut tracking-[0.06em]">
            {ticker} · {tradeDate}
          </div>
        </div>

        {/* Vertical divider */}
        <div className="hidden md:block bg-rule w-px"></div>

        {/* Right column: financial parameters & executive summary */}
        <div className="py-6 md:pl-10 flex flex-col justify-center gap-4">
          <div className="flex flex-wrap gap-x-10 gap-y-3">
            {verdict?.price_target && (
              <div className="fig">
                <span className="text-xs font-semibold tracking-[0.12em] uppercase text-faint block">
                  Price Target
                </span>
                <span className="text-2xl font-semibold tracking-tight text-ink num mt-1 block" data-testid="verdict-price-target">
                  {verdict.price_target}
                </span>
              </div>
            )}

            {verdict?.entry_price && (
              <div className="fig">
                <span className="text-xs font-semibold tracking-[0.12em] uppercase text-faint block">
                  Entry Price
                </span>
                <span className="text-2xl font-semibold tracking-tight text-ink num mt-1 block">
                  {verdict.entry_price}
                </span>
              </div>
            )}

            {verdict?.stop_loss && (
              <div className="fig">
                <span className="text-xs font-semibold tracking-[0.12em] uppercase text-faint block">
                  Stop Loss
                </span>
                <span className="text-2xl font-semibold tracking-tight text-ink num mt-1 block">
                  {verdict.stop_loss}
                </span>
              </div>
            )}

            {verdict?.position_sizing && (
              <div className="fig">
                <span className="text-xs font-semibold tracking-[0.12em] uppercase text-faint block">
                  Position Sizing
                </span>
                <span className="text-2xl font-semibold tracking-tight text-ink num mt-1 block">
                  {verdict.position_sizing}
                </span>
              </div>
            )}
          </div>

          {verdict?.executive_summary && (
            <p className="text-[13.5px] text-mut leading-relaxed max-w-3xl m-0" data-testid="verdict-summary">
              {verdict.executive_summary}
            </p>
          )}
        </div>
      </div>
    </section>
  );
};
