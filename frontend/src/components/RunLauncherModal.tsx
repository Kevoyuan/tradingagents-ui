import React, { useEffect, useMemo, useState } from 'react';
import { ProviderCatalog, UserPreferencesResponse } from '../types';

interface RunLauncherModalProps {
  isOpen: boolean;
  onClose: () => void;
  onStart: (params: {
    ticker: string;
    tradeDate: string;
    stepDelay: number;
    provider?: string;
    quickModel?: string;
    deepModel?: string;
    depth?: number;
    analysts?: string[];
    useStub?: boolean;
  }) => Promise<void>;
  isLoading: boolean;
}

export const RunLauncherModal: React.FC<RunLauncherModalProps> = ({
  isOpen,
  onClose,
  onStart,
  isLoading,
}) => {
  const [catalog, setCatalog] = useState<ProviderCatalog | null>(null);
  const [preferences, setPreferences] = useState<UserPreferencesResponse | null>(null);

  const [ticker, setTicker] = useState<string>('NBIS');
  const [tradeDate, setTradeDate] = useState<string>(() => new Date().toISOString().split('T')[0]);
  const [provider, setProvider] = useState<string>('deepseek');
  const [quickModel, setQuickModel] = useState<string>('deepseek-v4-flash');
  const [deepModel, setDeepModel] = useState<string>('deepseek-v4-flash');
  const [stepDelay, setStepDelay] = useState<number>(0.0);
  const [useStub, setUseStub] = useState<boolean>(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Fetch catalog and preferences when opened
  useEffect(() => {
    if (!isOpen) return;

    let mounted = true;
    async function init() {
      try {
        const [catRes, credRes] = await Promise.all([
          fetch('/api/providers'),
          fetch('/api/credentials'),
        ]);

        if (catRes.ok && credRes.ok && mounted) {
          const catData: ProviderCatalog = await catRes.json();
          const credData: UserPreferencesResponse = await credRes.json();

          setCatalog(catData);
          setPreferences(credData);

          if (credData.ticker) setTicker(credData.ticker);
          if (credData.llm_provider) setProvider(credData.llm_provider);
          if (credData.quick_think_llm) setQuickModel(credData.quick_think_llm);
          if (credData.deep_think_llm) setDeepModel(credData.deep_think_llm);
        }
      } catch {
        // Fallback to defaults if backend unavailable
      }
    }

    init();
    return () => {
      mounted = false;
    };
  }, [isOpen]);

  // Compute model choices for selected provider
  const modelChoices = useMemo(() => {
    if (!catalog) return { quick: [], deep: [] };
    const p = provider.toLowerCase();
    const provModels = catalog.provider_model_options?.[p] || catalog.upstream_model_options?.[p];
    return {
      quick: provModels?.quick || [
        ['DeepSeek V4 Flash', 'deepseek-v4-flash'],
        ['Custom model ID', 'custom'],
      ],
      deep: provModels?.deep || [
        ['DeepSeek V4 Pro', 'deepseek-v4-pro'],
        ['DeepSeek V4 Flash', 'deepseek-v4-flash'],
        ['Custom model ID', 'custom'],
      ],
    };
  }, [catalog, provider]);

  // When provider changes, sync default models if not customized
  const handleProviderChange = (newProvider: string) => {
    setProvider(newProvider);
    if (catalog) {
      const p = newProvider.toLowerCase();
      const provModels = catalog.provider_model_options?.[p] || catalog.upstream_model_options?.[p];
      if (provModels?.quick?.[0]) setQuickModel(provModels.quick[0][1]);
      if (provModels?.deep?.[0]) setDeepModel(provModels.deep[0][1]);
    }
  };

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!ticker.trim()) {
      setErrorMsg('Ticker is required');
      return;
    }
    setErrorMsg(null);
    try {
      const depthVal = preferences?.depth_key && catalog?.depth_options
        ? catalog.depth_options[preferences.depth_key] || 5
        : 5;

      await onStart({
        ticker: ticker.trim().toUpperCase(),
        tradeDate,
        stepDelay,
        provider,
        quickModel,
        deepModel,
        depth: depthVal,
        analysts: preferences?.analysts,
        useStub,
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
      <div className="bg-paper border border-ink p-8 w-full max-w-lg shadow-2xl font-grotesk">
        <div className="flex justify-between items-baseline mb-6 border-b border-rule pb-3">
          <div>
            <h2 id="modal-title" className="text-sm font-bold tracking-[0.14em] uppercase text-ink">
              Start Analysis Run
            </h2>
            <p className="text-xs text-mut mt-0.5">Launches research agents with configured models</p>
          </div>
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
          <div className="grid grid-cols-2 gap-4">
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
                placeholder="e.g. AAPL, FORM, NBIS"
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
          </div>

          <div>
            <label
              htmlFor="provider-select"
              className="block text-xs font-bold tracking-[0.12em] uppercase text-faint mb-1.5"
            >
              LLM Provider
            </label>
            <select
              id="provider-select"
              value={provider}
              onChange={(e) => handleProviderChange(e.target.value)}
              className="w-full px-3 py-2 border border-rule font-grotesk text-sm text-ink bg-page/50 focus:outline-none focus:border-ink"
              data-testid="launcher-provider"
            >
              {(catalog?.providers || [
                { id: 'deepseek', label: 'TradingAgents · DeepSeek', value: 'deepseek' },
                { id: 'openai', label: 'TradingAgents · OpenAI', value: 'openai' },
              ]).map((p) => (
                <option key={p.id} value={p.id}>
                  {p.label}
                </option>
              ))}
            </select>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label
                htmlFor="quick-model-select"
                className="block text-xs font-bold tracking-[0.12em] uppercase text-faint mb-1.5"
              >
                Quick Model
              </label>
              <select
                id="quick-model-select"
                value={quickModel}
                onChange={(e) => setQuickModel(e.target.value)}
                className="w-full px-3 py-2 border border-rule font-grotesk text-xs text-ink bg-page/50 focus:outline-none focus:border-ink"
                data-testid="launcher-quick-model"
              >
                {modelChoices.quick.map(([label, id]) => (
                  <option key={id} value={id}>
                    {label}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label
                htmlFor="deep-model-select"
                className="block text-xs font-bold tracking-[0.12em] uppercase text-faint mb-1.5"
              >
                Deep Model
              </label>
              <select
                id="deep-model-select"
                value={deepModel}
                onChange={(e) => setDeepModel(e.target.value)}
                className="w-full px-3 py-2 border border-rule font-grotesk text-xs text-ink bg-page/50 focus:outline-none focus:border-ink"
                data-testid="launcher-deep-model"
              >
                {modelChoices.deep.map(([label, id]) => (
                  <option key={id} value={id}>
                    {label}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div className="flex items-center justify-between pt-2">
            <div>
              <label
                htmlFor="step-delay-input"
                className="block text-xs font-bold tracking-[0.12em] uppercase text-faint mb-1"
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
                className="w-32 px-2.5 py-1.5 border border-rule font-grotesk text-xs text-ink bg-page/50 focus:outline-none focus:border-ink"
                data-testid="launcher-delay"
              />
            </div>

            <label className="flex items-center gap-2 cursor-pointer select-none text-xs text-mut mt-4">
              <input
                type="checkbox"
                checked={useStub}
                onChange={(e) => setUseStub(e.target.checked)}
                className="accent-ink"
                data-testid="launcher-stub-checkbox"
              />
              <span>Stub Run (Mock Data)</span>
            </label>
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
