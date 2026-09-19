import React, { useEffect, useMemo, useState } from 'react';
import { ProviderCatalog, UserPreferencesResponse } from '../types';

interface SettingsScreenProps {
  onNavigate: (path: string) => void;
  onClose?: () => void;
}

export const SettingsScreen: React.FC<SettingsScreenProps> = ({ onNavigate, onClose }) => {
  // Rendered as a modal drawer over the current screen. Closing returns to
  // whatever was behind it; onNavigate is the fallback for direct /settings hits.
  const close = onClose ?? (() => onNavigate('/'));

  // Standard modal manners, none of which were present: Escape dismisses, and
  // the page behind is locked so scrolling inside the drawer does not drag the
  // Monitor underneath it.
  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        event.preventDefault();
        (onClose ?? (() => onNavigate('/')))();
      }
    };
    document.addEventListener('keydown', onKeyDown);
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => {
      document.removeEventListener('keydown', onKeyDown);
      document.body.style.overflow = previousOverflow;
    };
  }, [onClose, onNavigate]);
  const [catalog, setCatalog] = useState<ProviderCatalog | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isSaving, setIsSaving] = useState<boolean>(false);
  const [saveStatus, setSaveStatus] = useState<'idle' | 'success' | 'error'>('idle');
  const [statusMessage, setStatusMessage] = useState<string>('');

  // Form states
  const [ticker, setTicker] = useState<string>('NBIS');
  const [analysisDate, setAnalysisDate] = useState<string>(() => new Date().toISOString().split('T')[0]);
  const [language, setLanguage] = useState<string>('English');
  const [selectedAnalysts, setSelectedAnalysts] = useState<string[]>([
    'market',
    'social',
    'news',
    'fundamentals',
  ]);
  const [depthKey, setDepthKey] = useState<string>('Deep (5 rounds)');
  const [provider, setProvider] = useState<string>('deepseek');
  const [quickModel, setQuickModel] = useState<string>('deepseek-v4-flash');
  const [deepModel, setDeepModel] = useState<string>('deepseek-v4-flash');

  // Per-credential edited values and visibility toggles
  const [credentialValues, setCredentialValues] = useState<Record<string, string>>({});
  const [credentialHints, setCredentialHints] = useState<Record<string, { is_set: boolean; hint: string }>>({});
  const [revealedCredentials, setRevealedCredentials] = useState<Record<string, boolean>>({});

  // Advanced settings & Data vendors
  const [checkpointEnabled, setCheckpointEnabled] = useState<boolean>(false);
  const [temperature, setTemperature] = useState<string>('');
  const [maxRetries, setMaxRetries] = useState<string>('');
  const [dataVendors, setDataVendors] = useState<Record<string, string>>({
    core_stock_apis: 'yfinance,alpha_vantage',
    technical_indicators: 'yfinance,alpha_vantage',
    fundamental_data: 'yfinance,alpha_vantage',
    news_data: 'yfinance,alpha_vantage',
    macro_data: 'fred',
    prediction_markets: 'polymarket',
  });

  // Load catalog and existing saved credentials/preferences on mount
  useEffect(() => {
    let mounted = true;

    async function loadData() {
      setIsLoading(true);
      try {
        const [catRes, credRes] = await Promise.all([
          fetch('/api/providers'),
          fetch('/api/credentials'),
        ]);

        if (!catRes.ok) throw new Error('Failed to load provider catalog');
        if (!credRes.ok) throw new Error('Failed to load credentials');

        const catData: ProviderCatalog = await catRes.json();
        const credData: UserPreferencesResponse = await credRes.json();

        if (!mounted) return;

        setCatalog(catData);

        // Populate preferences
        if (credData.ticker) setTicker(credData.ticker);
        if (credData.output_language) setLanguage(credData.output_language);
        if (credData.analysts && credData.analysts.length > 0) setSelectedAnalysts(credData.analysts);
        if (credData.depth_key) setDepthKey(credData.depth_key);
        if (credData.llm_provider) setProvider(credData.llm_provider);
        if (credData.quick_think_llm) setQuickModel(credData.quick_think_llm);
        if (credData.deep_think_llm) setDeepModel(credData.deep_think_llm);

        // Advanced settings
        if (credData.advanced_settings) {
          setCheckpointEnabled(Boolean(credData.advanced_settings.checkpoint_enabled));
          if (credData.advanced_settings.temperature !== null && credData.advanced_settings.temperature !== undefined) {
            setTemperature(String(credData.advanced_settings.temperature));
          }
          if (credData.advanced_settings.llm_max_retries !== null && credData.advanced_settings.llm_max_retries !== undefined) {
            setMaxRetries(String(credData.advanced_settings.llm_max_retries));
          }
        }

        // Data vendors
        if (credData.data_vendors) {
          setDataVendors((prev) => ({ ...prev, ...credData.data_vendors }));
        }

        // Credentials status and hints
        if (credData.credentials) {
          const hints: Record<string, { is_set: boolean; hint: string }> = {};
          for (const [key, item] of Object.entries(credData.credentials)) {
            hints[key] = { is_set: item.is_set, hint: item.hint || '' };
          }
          setCredentialHints(hints);
        }
      } catch (err: unknown) {
        if (!mounted) return;
        setSaveStatus('error');
        setStatusMessage(err instanceof Error ? err.message : 'Error loading settings');
      } finally {
        if (mounted) setIsLoading(false);
      }
    }

    loadData();
    return () => {
      mounted = false;
    };
  }, []);

  // Compute model choices for current provider
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

  // Compute credentials needed for current provider
  const providerFields = useMemo(() => {
    if (!catalog) return [];
    const fields: { env_name: string; label: string; placeholder: string; is_required: boolean }[] = [];

    // 1. API key field
    const apiKeyEnv = catalog.provider_api_key_env?.[provider];
    if (apiKeyEnv) {
      const isReq = !catalog.credential_requirements?.[provider]?.optional?.includes(apiKeyEnv);
      fields.push({
        env_name: apiKeyEnv,
        label: `${apiKeyEnv} (API Key)`,
        placeholder: 'Enter API Key',
        is_required: isReq,
      });
    }

    // 2. Base URL field (if supported)
    const baseUrlEnv = catalog.provider_base_url_env?.[provider];
    if (baseUrlEnv) {
      const defaultUrl = catalog.provider_urls?.[provider] || '';
      fields.push({
        env_name: baseUrlEnv,
        label: `${baseUrlEnv} (Base URL)`,
        placeholder: defaultUrl || 'https://api.example.com/v1',
        is_required: !defaultUrl,
      });
    }

    // 3. Azure specific fields
    if (provider === 'azure') {
      for (const item of catalog.azure_env_fields || []) {
        fields.push({
          env_name: item.name,
          label: item.label,
          placeholder: item.placeholder,
          is_required: true,
        });
      }
    }

    // 4. Bedrock specific fields
    if (provider === 'bedrock') {
      for (const item of catalog.bedrock_env_fields || []) {
        fields.push({
          env_name: item.name,
          label: item.label,
          placeholder: item.placeholder,
          is_required: !item.optional,
        });
      }
    }

    return fields;
  }, [catalog, provider]);

  const toggleAnalyst = (key: string) => {
    setSelectedAnalysts((prev) =>
      prev.includes(key) ? prev.filter((k) => k !== key) : [...prev, key]
    );
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSaving(true);
    setSaveStatus('idle');
    setStatusMessage('');

    try {
      const payload: Record<string, any> = {
        ticker: ticker.trim().toUpperCase(),
        output_language: language,
        analysts: selectedAnalysts,
        depth_key: depthKey,
        llm_provider: provider,
        quick_think_llm: quickModel,
        deep_think_llm: deepModel,
        advanced_settings: {
          checkpoint_enabled: checkpointEnabled,
          temperature: temperature !== '' ? parseFloat(temperature) : null,
          llm_max_retries: maxRetries !== '' ? parseInt(maxRetries, 10) : null,
        },
        data_vendors: dataVendors,
        credentials: {},
      };

      // Only include credential fields that were explicitly typed into and non-empty
      for (const [key, val] of Object.entries(credentialValues)) {
        if (val && !val.includes('••••')) {
          payload.credentials[key] = val.trim();
        }
      }

      const res = await fetch('/api/credentials', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        throw new Error(`Failed to save settings: ${res.statusText}`);
      }

      const updated: UserPreferencesResponse = await res.json();
      // Update hints
      if (updated.credentials) {
        const hints: Record<string, { is_set: boolean; hint: string }> = {};
        for (const [key, item] of Object.entries(updated.credentials)) {
          hints[key] = { is_set: item.is_set, hint: item.hint || '' };
        }
        setCredentialHints(hints);
      }

      // Clear dirty inputs after saving
      setCredentialValues({});
      setSaveStatus('success');
      setStatusMessage('Settings saved successfully to disk.');
    } catch (err: unknown) {
      setSaveStatus('error');
      setStatusMessage(err instanceof Error ? err.message : 'Error saving settings');
    } finally {
      setIsSaving(false);
    }
  };

  if (isLoading) {
    return (
      <div className="p-8 max-w-4xl mx-auto font-grotesk text-ink">
        <div className="text-xs uppercase tracking-widest text-faint">Loading Preferences...</div>
      </div>
    );
  }

  return (
    <>
      <div
        className="fixed inset-y-0 right-0 left-14 z-40 bg-[rgba(10,10,10,.38)]"
        onClick={close}
        data-testid="settings-scrim"
        aria-hidden="true"
      />
      <aside
        role="dialog"
        aria-modal="true"
        aria-label="Settings"
        className="fixed left-14 top-0 bottom-0 z-50 w-[840px] max-w-[calc(92vw-3.5rem)] bg-paper border-r border-ink flex flex-col font-grotesk text-ink"
        data-testid="settings-drawer"
      >
        <header className="flex-none h-[56px] border-b border-ink px-6 flex items-center gap-3">
          <h1 className="text-[12px] font-bold tracking-[0.16em] uppercase text-ink">Settings</h1>
          <span className="font-mono text-[11px] text-faint">saved locally</span>
          <button
            type="button"
            onClick={close}
            aria-label="Close settings"
            className="ml-auto w-[26px] h-[26px] grid place-items-center border border-rule bg-paper text-ink hover:bg-page cursor-pointer"
            data-testid="settings-close"
          >
            ✕
          </button>
        </header>

        <div className="flex-none border-b border-rule bg-page px-6 py-2.5">
          <div className="text-[11px] font-bold tracking-[0.14em] uppercase text-faint">Next run</div>
          <div className="font-mono text-[12.5px] mt-1 truncate text-ink" data-testid="settings-next-run">
            {ticker} · {analysisDate} · {language} · {depthKey} · {provider} · {quickModel}
          </div>
        </div>

        <div className="flex-1 min-h-0 overflow-y-auto px-6 pb-1 pt-0" data-testid="settings-body">
        {saveStatus === 'success' && (
          <div className="mb-6 p-3 bg-green-50 border border-green-600 text-green-800 text-xs font-medium" data-testid="save-success-banner">
            ✓ {statusMessage}
          </div>
        )}
        {saveStatus === 'error' && (
          <div className="mb-6 p-3 bg-red-50 border border-sell text-sell text-xs font-medium" data-testid="save-error-banner">
            ✕ {statusMessage}
          </div>
        )}

        <form id="settings-form" onSubmit={handleSave} className="space-y-0">
          {/* Section 1: Analysis Parameters */}
          <section className="border-b border-rule py-1">
            <h2 className="text-xs font-bold uppercase tracking-[0.14em] text-ink mb-1 pb-1 border-b border-ink">
              1. Analysis Parameters
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-2">
              <div>
                <label htmlFor="settings-ticker" className="block text-xs font-bold uppercase tracking-wider text-faint mb-1">
                  Default Ticker Symbol
                </label>
                <input
                  id="settings-ticker"
                  data-testid="settings-ticker"
                  type="text"
                  value={ticker}
                  onChange={(e) => setTicker(e.target.value)}
                  className="w-full px-3 py-1.5 border border-rule font-grotesk text-sm text-ink bg-paper focus:outline-none focus:border-ink"
                  required
                />
              </div>

              <div>
                <label htmlFor="settings-date" className="block text-xs font-bold uppercase tracking-wider text-faint mb-1">
                  Analysis Trade Date
                </label>
                <input
                  id="settings-date"
                  data-testid="settings-date"
                  type="date"
                  value={analysisDate}
                  onChange={(e) => setAnalysisDate(e.target.value)}
                  className="w-full px-3 py-1.5 border border-rule font-grotesk text-sm text-ink bg-paper focus:outline-none focus:border-ink"
                  required
                />
              </div>

              <div>
                <label htmlFor="settings-language" className="block text-xs font-bold uppercase tracking-wider text-faint mb-1">
                  Output Language
                </label>
                <select
                  id="settings-language"
                  data-testid="settings-language"
                  value={language}
                  onChange={(e) => setLanguage(e.target.value)}
                  className="w-full px-3 py-1.5 border border-rule font-grotesk text-sm text-ink bg-paper focus:outline-none focus:border-ink"
                >
                  {(catalog?.languages || ['English', 'Chinese']).map((lang) => (
                    <option key={lang} value={lang}>
                      {lang}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label htmlFor="settings-depth" className="block text-xs font-bold uppercase tracking-wider text-faint mb-1">
                  Research Depth
                </label>
                <select
                  id="settings-depth"
                  data-testid="settings-depth"
                  value={depthKey}
                  onChange={(e) => setDepthKey(e.target.value)}
                  className="w-full px-3 py-1.5 border border-rule font-grotesk text-sm text-ink bg-paper focus:outline-none focus:border-ink"
                >
                  {Object.keys(catalog?.depth_options || { 'Deep (5 rounds)': 5 }).map((dk) => (
                    <option key={dk} value={dk}>
                      {dk}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <div className="mt-5">
              <span className="block text-xs font-bold uppercase tracking-wider text-faint mb-2">
                Active Analysts
              </span>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
                {(catalog?.analyst_options || [
                  { id: 'market', label: 'Market Analyst', value: 'market' },
                  { id: 'social', label: 'Social Media Analyst', value: 'social' },
                  { id: 'news', label: 'News Analyst', value: 'news' },
                  { id: 'fundamentals', label: 'Fundamentals Analyst', value: 'fundamentals' },
                ]).map((analyst) => (
                  <label
                    key={analyst.id}
                    className="flex items-center gap-2 p-2.5 border border-rule bg-paper cursor-pointer select-none text-xs hover:border-ink transition-colors"
                  >
                    <input
                      type="checkbox"
                      checked={selectedAnalysts.includes(analyst.id)}
                      onChange={() => toggleAnalyst(analyst.id)}
                      className="accent-ink"
                    />
                    <span className="font-medium text-ink">{analyst.label}</span>
                  </label>
                ))}
              </div>
            </div>
          </section>

          {/* Section 2: LLM Provider & Models */}
          <section className="border-b border-rule py-1">
            <h2 className="text-xs font-bold uppercase tracking-[0.14em] text-ink mb-1 pb-1 border-b border-ink">
              2. LLM Provider & Models
            </h2>

            <div className="space-y-4">
              <div>
                <label htmlFor="settings-provider" className="block text-xs font-bold uppercase tracking-wider text-faint mb-1">
                  LLM Provider
                </label>
                <select
                  id="settings-provider"
                  data-testid="settings-provider"
                  value={provider}
                  onChange={(e) => setProvider(e.target.value)}
                  className="w-full px-3 py-1.5 border border-rule font-grotesk text-sm text-ink bg-paper focus:outline-none focus:border-ink"
                >
                  {(catalog?.providers || [{ id: 'deepseek', label: 'TradingAgents · DeepSeek', value: 'deepseek' }]).map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.label}
                    </option>
                  ))}
                </select>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-2">
                <div>
                  <label htmlFor="settings-quick-model" className="block text-xs font-bold uppercase tracking-wider text-faint mb-1">
                    Quick-Think Model
                  </label>
                  <select
                    id="settings-quick-model"
                    data-testid="settings-quick-model"
                    value={quickModel}
                    onChange={(e) => setQuickModel(e.target.value)}
                    className="w-full px-3 py-1.5 border border-rule font-grotesk text-sm text-ink bg-paper focus:outline-none focus:border-ink"
                  >
                    {modelChoices.quick.map(([label, id]) => (
                      <option key={id} value={id}>
                        {label} ({id})
                      </option>
                    ))}
                  </select>
                  {quickModel === 'custom' && (
                    <input
                      type="text"
                      placeholder="Enter custom quick model ID"
                      onChange={(e) => setQuickModel(e.target.value)}
                      className="mt-2 w-full px-3 py-1.5 border border-rule font-grotesk text-xs bg-paper"
                    />
                  )}
                </div>

                <div>
                  <label htmlFor="settings-deep-model" className="block text-xs font-bold uppercase tracking-wider text-faint mb-1">
                    Deep-Think Model
                  </label>
                  <select
                    id="settings-deep-model"
                    data-testid="settings-deep-model"
                    value={deepModel}
                    onChange={(e) => setDeepModel(e.target.value)}
                    className="w-full px-3 py-1.5 border border-rule font-grotesk text-sm text-ink bg-paper focus:outline-none focus:border-ink"
                  >
                    {modelChoices.deep.map(([label, id]) => (
                      <option key={id} value={id}>
                        {label} ({id})
                      </option>
                    ))}
                  </select>
                  {deepModel === 'custom' && (
                    <input
                      type="text"
                      placeholder="Enter custom deep model ID"
                      onChange={(e) => setDeepModel(e.target.value)}
                      className="mt-2 w-full px-3 py-1.5 border border-rule font-grotesk text-xs bg-paper"
                    />
                  )}
                </div>
              </div>
            </div>
          </section>

          {/* Section 3: Credentials for Selected Provider */}
          <section className="border-b border-rule py-1">
            <h2 className="text-xs font-bold uppercase tracking-[0.14em] text-ink mb-2 pb-2 border-b border-rule flex justify-between items-center">
              <span>3. Credentials & Keys ({provider})</span>
              <span className="text-[11px] font-normal lowercase text-mut">Saved to ~/.tradingagents/.env</span>
            </h2>

            {providerFields.length === 0 ? (
              <p className="text-xs text-mut py-3">No credentials required for this provider.</p>
            ) : (
              <div className="space-y-4 mt-4">
                {providerFields.map((field) => {
                  const hintInfo = credentialHints[field.env_name];
                  const isConfigured = hintInfo?.is_set;
                  const isRevealed = Boolean(revealedCredentials[field.env_name]);
                  const currentValue = credentialValues[field.env_name] || '';

                  return (
                    <div key={field.env_name} className="p-4 border border-rule bg-paper">
                      <div className="flex justify-between items-center mb-1.5">
                        <label
                          htmlFor={`cred-${field.env_name}`}
                          className="text-xs font-bold uppercase tracking-wider text-ink"
                        >
                          {field.label}
                          {field.is_required && <span className="text-sell ml-1">*</span>}
                        </label>
                        <span
                          className={`text-[10px] uppercase font-bold tracking-widest px-2 py-0.5 border ${
                            isConfigured
                              ? 'border-green-600 bg-green-50 text-green-800'
                              : 'border-rule bg-page text-mut'
                          }`}
                          data-testid={`cred-status-${field.env_name}`}
                        >
                          {isConfigured ? `Configured (${hintInfo.hint})` : 'Not Configured'}
                        </span>
                      </div>

                      <div className="relative flex items-center">
                        <input
                          id={`cred-${field.env_name}`}
                          data-testid={`cred-input-${field.env_name}`}
                          type={isRevealed ? 'text' : 'password'}
                          value={currentValue}
                          placeholder={field.placeholder}
                          onChange={(e) =>
                            setCredentialValues((prev) => ({
                              ...prev,
                              [field.env_name]: e.target.value,
                            }))
                          }
                          className="w-full pr-16 px-3 py-1.5 border border-ink font-grotesk text-sm text-ink bg-paper focus:outline-none focus:ring-1 focus:ring-ink"
                        />
                        <button
                          type="button"
                          onClick={() =>
                            setRevealedCredentials((prev) => ({
                              ...prev,
                              [field.env_name]: !prev[field.env_name],
                            }))
                          }
                          className="absolute right-2 px-2 py-1 text-[11px] font-semibold uppercase tracking-wider text-mut hover:text-ink bg-paper border border-rule cursor-pointer"
                        >
                          {isRevealed ? 'Hide' : 'Show'}
                        </button>
                      </div>
                      <p className="text-[11px] text-mut mt-1.5" data-testid={`cred-hint-${field.env_name}`}>
                        {isConfigured
                          ? `已保存 ${hintInfo.hint} — 留空则保持不变，填入新值则覆盖`
                          : '尚未配置 — 在此粘贴 API key'}
                      </p>
                    </div>
                  );
                })}
              </div>
            )}
          </section>

          {/* Section 4: Advanced Settings & Data Vendors */}
          <section className="border-b border-rule py-1">
            <h2 className="text-xs font-bold uppercase tracking-[0.14em] text-ink mb-1 pb-1 border-b border-ink">
              4. Advanced Settings & Data Vendors
            </h2>

            <div className="space-y-4">
              <label className="flex items-center gap-2 p-2 border border-rule bg-paper cursor-pointer select-none text-xs">
                <input
                  type="checkbox"
                  checked={checkpointEnabled}
                  onChange={(e) => setCheckpointEnabled(e.target.checked)}
                  className="accent-ink"
                />
                <span className="font-semibold text-ink">Enable Graph Checkpoints</span>
              </label>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-2">
                <div>
                  <label htmlFor="settings-temp" className="block text-xs font-bold uppercase tracking-wider text-faint mb-1">
                    Temperature (Optional)
                  </label>
                  <input
                    id="settings-temp"
                    type="number"
                    step="0.1"
                    min="0"
                    max="2"
                    placeholder="0.7"
                    value={temperature}
                    onChange={(e) => setTemperature(e.target.value)}
                    className="w-full px-3 py-1.5 border border-rule font-grotesk text-sm text-ink bg-paper focus:outline-none focus:border-ink"
                  />
                </div>

                <div>
                  <label htmlFor="settings-retries" className="block text-xs font-bold uppercase tracking-wider text-faint mb-1">
                    LLM Max Retries (Optional)
                  </label>
                  <input
                    id="settings-retries"
                    type="number"
                    min="1"
                    max="10"
                    placeholder="3"
                    value={maxRetries}
                    onChange={(e) => setMaxRetries(e.target.value)}
                    className="w-full px-3 py-1.5 border border-rule font-grotesk text-sm text-ink bg-paper focus:outline-none focus:border-ink"
                  />
                </div>
              </div>

              <div className="pt-3 border-t border-rule">
                <span className="block text-xs font-bold uppercase tracking-wider text-faint mb-2">
                  Data Vendor Sources
                </span>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-2">
                  {Object.entries(dataVendors).map(([vendorKey, vendorVal]) => (
                    <div key={vendorKey}>
                      <label htmlFor={`vendor-${vendorKey}`} className="block text-[11px] font-semibold text-mut uppercase mb-1">
                        {vendorKey.replace(/_/g, ' ')}
                      </label>
                      <input
                        id={`vendor-${vendorKey}`}
                        type="text"
                        value={vendorVal}
                        onChange={(e) =>
                          setDataVendors((prev) => ({
                            ...prev,
                            [vendorKey]: e.target.value,
                          }))
                        }
                        className="w-full px-2.5 py-1.5 border border-rule font-grotesk text-xs text-ink bg-paper focus:outline-none focus:border-ink"
                      />
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </section>

        </form>
        </div>

        {/* Pinned actions. Outside the scroll area so Save is always reachable
            and the body only ever has to fit the configuration itself. */}
        <footer className="flex-none border-t border-ink px-6 py-3 flex items-center gap-3">
          <span className="font-mono text-[11px] text-mut" data-testid="settings-dirty">
            {isSaving ? 'saving…' : 'writes ~/.tradingagents/ui_preferences.json'}
          </span>
          <button
            type="button"
            onClick={close}
            className="ml-auto px-4 py-2 text-[11px] font-semibold uppercase tracking-wider border border-ink bg-transparent text-ink hover:bg-page cursor-pointer transition-colors"
          >
            Discard
          </button>
          <button
            type="submit"
            form="settings-form"
            disabled={isSaving}
            className="px-4 py-2 text-[11px] font-bold uppercase tracking-wider bg-ink text-paper border border-ink hover:bg-transparent hover:text-ink cursor-pointer disabled:opacity-50 transition-colors"
            data-testid="settings-save-button"
          >
            {isSaving ? 'Saving…' : 'Save preferences'}
          </button>
        </footer>
      </aside>
    </>
  );
};
