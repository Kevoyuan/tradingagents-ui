import React, { useState } from 'react';

interface RunLauncherModalProps {
  isOpen: boolean;
  onClose: () => void;
  onStart: (params: { ticker: string; tradeDate: string; stepDelay: number }) => Promise<void>;
  isLoading: boolean;
}

export const RunLauncherModal: React.FC<RunLauncherModalProps> = ({
  isOpen,
  onClose,
  onStart,
  isLoading,
}) => {
  const [ticker, setTicker] = useState<string>('FORM');
  const [tradeDate, setTradeDate] = useState<string>('2026-05-05');
  const [stepDelay, setStepDelay] = useState<number>(0.0);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!ticker.trim()) {
      setErrorMsg('Ticker is required');
      return;
    }
    setErrorMsg(null);
    try {
      await onStart({
        ticker: ticker.trim().toUpperCase(),
        tradeDate,
        stepDelay,
      });
      onClose();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to start run';
      setErrorMsg(msg);
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm"
      role="dialog"
      aria-modal="true"
      aria-labelledby="modal-title"
    >
      <div className="bg-paper border border-ink p-8 w-full max-w-md shadow-2xl">
        <div className="flex justify-between items-baseline mb-6 border-b border-rule pb-3">
          <h2 id="modal-title" className="text-sm font-bold tracking-[0.14em] uppercase text-ink">
            Start New Run
          </h2>
          <button
            type="button"
            onClick={onClose}
            className="text-xs font-bold uppercase text-faint hover:text-ink cursor-pointer bg-transparent border-0"
          >
            Close
          </button>
        </div>

        {errorMsg && (
          <div className="mb-4 p-2.5 bg-red-50 border border-sell text-sell text-xs">
            {errorMsg}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label
              htmlFor="ticker-input"
              className="block text-xs font-bold tracking-[0.12em] uppercase text-faint mb-1.5"
            >
              Ticker Symbol
            </label>
            <input
              id="ticker-input"
              type="text"
              value={ticker}
              onChange={(e) => setTicker(e.target.value)}
              placeholder="e.g. AAPL, FORM, MSFT"
              className="w-full px-3 py-2 border border-rule font-grotesk text-sm text-ink bg-page/50 focus:outline-none focus:border-ink"
              required
              data-testid="launcher-ticker"
            />
          </div>

          <div>
            <label
              htmlFor="trade-date-input"
              className="block text-xs font-bold tracking-[0.12em] uppercase text-faint mb-1.5"
            >
              Trade Date
            </label>
            <input
              id="trade-date-input"
              type="date"
              value={tradeDate}
              onChange={(e) => setTradeDate(e.target.value)}
              className="w-full px-3 py-2 border border-rule font-grotesk text-sm text-ink bg-page/50 focus:outline-none focus:border-ink"
              required
              data-testid="launcher-date"
            />
          </div>

          <div>
            <label
              htmlFor="step-delay-input"
              className="block text-xs font-bold tracking-[0.12em] uppercase text-faint mb-1.5"
            >
              Step Delay (seconds)
            </label>
            <input
              id="step-delay-input"
              type="number"
              step="0.01"
              min="0"
              value={stepDelay}
              onChange={(e) => setStepDelay(parseFloat(e.target.value) || 0)}
              className="w-full px-3 py-2 border border-rule font-grotesk text-sm text-ink bg-page/50 focus:outline-none focus:border-ink"
              data-testid="launcher-delay"
            />
          </div>

          <div className="pt-4 flex justify-end gap-3 border-t border-rule">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-xs font-semibold uppercase tracking-wider border border-rule bg-transparent text-mut hover:border-ink hover:text-ink cursor-pointer"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isLoading}
              className="px-5 py-2 text-xs font-bold uppercase tracking-wider bg-ink text-paper border border-ink hover:bg-transparent hover:text-ink cursor-pointer disabled:opacity-50 transition-colors"
              data-testid="launcher-submit"
            >
              {isLoading ? 'Starting...' : 'Start Run'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
