import React, { useEffect, useRef, useState } from 'react';
import { ExportStatus } from '../types';

interface ReportExportWidgetProps {
  ticker: string;
  date: string;
}

export const ReportExportWidget: React.FC<ReportExportWidgetProps> = ({ ticker, date }) => {
  const [status, setStatus] = useState<ExportStatus>({ state: 'idle', error: null });
  const [isSubmitting, setIsSubmitting] = useState(false);
  const pollingRef = useRef<number | null>(null);

  const stopPolling = () => {
    if (pollingRef.current !== null) {
      window.clearInterval(pollingRef.current);
      pollingRef.current = null;
    }
  };

  const checkStatus = async () => {
    try {
      const res = await fetch(`/api/reports/${encodeURIComponent(ticker)}/${encodeURIComponent(date)}/export/status`);
      if (res.ok) {
        const data: ExportStatus = await res.json();
        setStatus(data);
        if (data.state === 'ready' || data.state === 'failed') {
          stopPolling();
        }
      }
    } catch {
      // Export failure must never break reading; ignore network glitches
    }
  };

  // Poll when status is running
  useEffect(() => {
    checkStatus();

    return () => {
      stopPolling();
    };
  }, [ticker, date]);

  useEffect(() => {
    if (status.state === 'running') {
      if (pollingRef.current === null) {
        pollingRef.current = window.setInterval(checkStatus, 1000);
      }
    } else {
      stopPolling();
    }
  }, [status.state]);

  const handleStartExport = async () => {
    if (status.state === 'running' || isSubmitting) return;

    setIsSubmitting(true);
    try {
      const res = await fetch(`/api/reports/${encodeURIComponent(ticker)}/${encodeURIComponent(date)}/export`, {
        method: 'POST',
      });
      if (res.status === 202) {
        setStatus({ state: 'running', error: null });
      } else {
        const errJson = await res.json().catch(() => null);
        const errMsg = errJson?.detail || `Export failed with status ${res.status}`;
        setStatus({ state: 'failed', error: errMsg });
      }
    } catch (err) {
      setStatus({ state: 'failed', error: String(err) });
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleOpenHtml = () => {
    window.open(`/api/reports/${encodeURIComponent(ticker)}/${encodeURIComponent(date)}/export`, '_blank');
  };

  return (
    <div
      className="flex flex-col sm:flex-row sm:items-center gap-3"
      data-testid="export-widget"
      aria-label="Report Export"
    >
      {/* State 1: Ready - open cached HTML */}
      {status.state === 'ready' && (
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={handleOpenHtml}
            className="font-grotesk text-xs font-semibold tracking-[0.13em] uppercase bg-ink text-paper py-2 px-4 cursor-pointer hover:bg-ink-2 transition-colors border border-ink"
            data-testid="open-export-button"
          >
            Open HTML Report ↗
          </button>
          <button
            type="button"
            onClick={handleStartExport}
            className="font-grotesk text-xs font-semibold tracking-[0.13em] uppercase bg-transparent text-mut py-2 px-3 cursor-pointer hover:text-ink transition-colors border border-rule"
            data-testid="re-export-button"
            title="Re-generate HTML export"
          >
            Re-export
          </button>
        </div>
      )}

      {/* State 2: Running */}
      {status.state === 'running' && (
        <div className="flex items-center gap-2.5 text-xs text-mut font-semibold tracking-[0.08em] uppercase py-2 px-3 border border-rule bg-page" data-testid="export-running">
          <span className="inline-block w-2.5 h-2.5 border-2 border-mut border-t-transparent rounded-full animate-spin"></span>
          <span>Generating HTML...</span>
        </div>
      )}

      {/* State 3: Idle */}
      {status.state === 'idle' && (
        <button
          type="button"
          onClick={handleStartExport}
          disabled={isSubmitting}
          className="font-grotesk text-xs font-semibold tracking-[0.13em] uppercase bg-transparent border border-ink text-ink py-2 px-4 cursor-pointer hover:bg-ink hover:text-paper transition-colors disabled:opacity-50"
          data-testid="export-button"
        >
          {isSubmitting ? 'Starting...' : 'Export HTML'}
        </button>
      )}

      {/* State 4: Failed with error (Reading is never broken) */}
      {status.state === 'failed' && (
        <div className="flex flex-col sm:flex-row items-start sm:items-center gap-2" data-testid="export-failed">
          <div className="text-xs text-sell font-medium px-2 py-1 bg-sell/10 border border-sell/30">
            Export failed: {status.error || 'Unknown error'}
          </div>
          <button
            type="button"
            onClick={handleStartExport}
            className="font-grotesk text-xs font-semibold tracking-[0.13em] uppercase bg-transparent border border-ink text-ink py-1.5 px-3 cursor-pointer hover:bg-ink hover:text-paper transition-colors"
            data-testid="retry-export-button"
          >
            Retry
          </button>
        </div>
      )}
    </div>
  );
};
