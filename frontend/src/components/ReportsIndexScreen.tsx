import React, { useEffect, useState } from 'react';
import { ReportSummary } from '../types';

interface ReportsIndexScreenProps {
  onNavigate: (path: string) => void;
  /**
   * Changes when the selected run reaches a terminal state.
   *
   * The index was fetched once on mount, so a run started from the Settings
   * drawer (a modal over this screen) finished while the user sat on a list
   * that could not contain it, and the new report looked missing until they
   * navigated away and back.
   */
  refreshKey?: string;
}

export const ReportsIndexScreen: React.FC<ReportsIndexScreenProps> = ({ onNavigate, refreshKey = '' }) => {
  const [reports, setReports] = useState<ReportSummary[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    setError(null);

    fetch('/api/reports')
      .then(async (res) => {
        if (!res.ok) {
          throw new Error(`HTTP ${res.status}: Failed to list reports`);
        }
        return res.json();
      })
      .then((data: ReportSummary[]) => {
        setReports(data || []);
        setLoading(false);
      })
      .catch((err) => {
        setError(err.message || String(err));
        setLoading(false);
      });
  }, [refreshKey]);

  return (
    <div className="min-h-screen bg-paper flex flex-col font-grotesk" data-testid="reports-index-screen">
      {/* Masthead-like header */}
      <header className="h-[62px] flex items-center justify-between px-10 border-b border-ink bg-paper sticky top-0 z-30 select-none">
        <div className="flex items-center gap-6">
          <span className="text-[13px] font-bold tracking-[0.15em] uppercase text-ink">
            TradingAgents
          </span>
          <nav className="flex gap-5" aria-label="Reports Navigation">
            <button
              type="button"
              onClick={() => onNavigate('/')}
              className="text-xs font-medium tracking-[0.13em] uppercase text-faint hover:text-ink transition-colors bg-transparent border-0 cursor-pointer p-0"
            >
              Monitor
            </button>
            <span
              aria-current="page"
              className="text-xs font-bold tracking-[0.13em] uppercase text-ink cursor-default"
            >
              Reports
            </span>
          </nav>
        </div>

        <div className="text-xs text-mut tracking-wider font-semibold uppercase">
          {reports.length} {reports.length === 1 ? 'REPORT' : 'REPORTS'} ARCHIVED
        </div>
      </header>

      {/* Main Container */}
      <main className="p-10 max-w-5xl">
        <div className="border-b border-ink pb-3 mb-8">
          <h1 className="text-2xl font-bold tracking-tight text-ink m-0">
            Historical Analysis Reports
          </h1>
          <p className="text-sm text-mut mt-1.5 m-0">
            Reports discovered in logs archive with extracted verdicts and complete evidence trees.
          </p>
        </div>

        {loading && (
          <div className="py-12 text-center text-mut text-xs font-semibold tracking-wider uppercase" data-testid="reports-loading">
            Loading reports index...
          </div>
        )}

        {error && (
          <div className="p-4 border border-sell/40 bg-sell/5 text-sell text-sm">
            Failed to load reports: {error}
          </div>
        )}

        {!loading && !error && reports.length === 0 && (
          <div className="py-16 text-center text-mut" data-testid="reports-empty">
            <div className="text-base font-semibold text-ink mb-1">No reports found</div>
            <p className="text-xs text-faint max-w-md mx-auto m-0">
              Completed runs automatically save multi-agent analysis reports to the logs directory.
            </p>
          </div>
        )}

        {!loading && !error && reports.length > 0 && (
          <div className="border border-rule divide-y divide-rule bg-paper shadow-sm" data-testid="reports-table">
            <div className="grid grid-cols-[140px_140px_1fr_120px] px-5 py-3 bg-page text-xs font-bold tracking-[0.13em] uppercase text-faint select-none">
              <div>Ticker</div>
              <div>Trade Date</div>
              <div>Verdict Rating</div>
              <div className="text-right">Sections</div>
            </div>

            {reports.map((rep) => {
              const rating = rep.verdict?.rating;
              let ratingColor = 'text-hold bg-hold/10 border-hold/30';
              if (rating === 'Buy' || rating === 'Overweight') {
                ratingColor = 'text-buy bg-buy/10 border-buy/30';
              } else if (rating === 'Underweight' || rating === 'Sell') {
                ratingColor = 'text-sell bg-sell/10 border-sell/30';
              }

              return (
                <div
                  key={`${rep.ticker}-${rep.trade_date}`}
                  onClick={() => onNavigate(`/reports/${rep.ticker}/${rep.trade_date}`)}
                  className="grid grid-cols-[140px_140px_1fr_120px] px-5 py-4 items-center hover:bg-page/40 transition-colors cursor-pointer text-sm"
                  data-testid={`report-row-${rep.ticker}-${rep.trade_date}`}
                >
                  <div className="font-bold tracking-tight text-ink text-base">
                    {rep.ticker}
                  </div>
                  <div className="text-mut text-xs tracking-wider num font-mono">
                    {rep.trade_date}
                  </div>
                  <div className="flex items-center gap-2">
                    {rating ? (
                      <span className={`px-2 py-0.5 text-xs font-semibold tracking-wider uppercase border ${ratingColor}`}>
                        {rating}
                      </span>
                    ) : (
                      <span className="text-xs text-faint italic">Pending / None</span>
                    )}
                    {rep.verdict?.price_target && (
                      <span className="text-xs text-mut num">
                        target: {rep.verdict.price_target}
                      </span>
                    )}
                  </div>
                  <div className="text-right text-xs text-mut font-semibold tracking-wider num">
                    {rep.sections_count} sections →
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </main>
    </div>
  );
};
