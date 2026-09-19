export type EventKind =
  | 'run_state'
  | 'agent_status'
  | 'agent_message'
  | 'user_message'
  | 'tool_call'
  | 'tool_result'
  | 'stats'
  | 'report_section'
  | 'verdict'
  | 'error';

export type TeamName = 'analyst' | 'research' | 'trading' | 'risk' | 'portfolio';

export type RunStatus = 'pending' | 'running' | 'completed' | 'cancelled' | 'failed';

export type VerdictRating = 'Buy' | 'Overweight' | 'Hold' | 'Underweight' | 'Sell';

export type SourceSection = 'portfolio' | 'trader';

export interface Verdict {
  rating: VerdictRating;
  source_section: SourceSection;
  price_target?: string | null;
  executive_summary?: string | null;
  entry_price?: string | null;
  stop_loss?: string | null;
  position_sizing?: string | null;
}

export interface RunStats {
  llm_calls?: number;
  tool_calls?: number;
  tokens_in?: number;
  tokens_out?: number;
  cost_usd?: number | null;
}

export interface RunEvent {
  seq: number;
  ts: string;
  run_id: string;
  kind: EventKind;
  agent?: string | null;
  team?: TeamName | null;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  payload: Record<string, any>;
}

export interface RunHeader {
  run_id: string;
  status: RunStatus;
  ticker: string;
  trade_date: string;
  created_at: string;
  started_at?: string | null;
  completed_at?: string | null;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  config: Record<string, any>;
  stats?: RunStats | null;
  verdict?: Verdict | null;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  error?: Record<string, any> | null;
}

export type AgentStatus = 'pending' | 'running' | 'done' | 'failed';

export interface AgentInfo {
  slug: string;
  name: string;
  team: TeamName;
  status: AgentStatus;
  tokens: number;
  activity?: string;
}

export interface StageInfo {
  name: string;
  team: TeamName;
  completed: number;
  total: number;
  status: 'done' | 'now' | 'pending';
}

export interface ToolEvidenceItem {
  tool: string;
  call_id: string;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  args?: any;
  ok?: boolean;
  duration_ms?: number;
  result?: string;
  truncated?: boolean;
  full_ref?: string | null;
}

export interface AgentBlock {
  name: string;
  slug: string;
  markdown: string;
  complete: boolean;
}

export interface ReportSection {
  title: string;
  slug: string;
  blocks: AgentBlock[];
}

export interface ReportSummary {
  ticker: string;
  trade_date: string;
  path: string;
  verdict?: Verdict | null;
  sections_count: number;
}

export interface ReportDetail {
  ticker: string;
  trade_date: string;
  verdict?: Verdict | null;
  sections: ReportSection[];
}

export type ExportState = 'idle' | 'running' | 'ready' | 'failed';

export interface ExportStatus {
  state: ExportState;
  error?: string | null;
}

export interface ProviderOption {
  id: string;
  label: string;
  value: string;
}

export interface CredentialStatus {
  is_set: boolean;
  is_secret: boolean;
  hint: string;
  value?: string;
}

export interface ProviderCatalog {
  providers: ProviderOption[];
  provider_model_options: Record<string, { quick: [string, string][]; deep: [string, string][] }>;
  upstream_model_options: Record<string, { quick: [string, string][]; deep: [string, string][] }>;
  provider_api_key_env: Record<string, string>;
  provider_base_url_env: Record<string, string>;
  provider_urls: Record<string, string | null>;
  azure_env_fields: { name: string; label: string; placeholder: string }[];
  bedrock_env_fields: { name: string; label: string; placeholder: string; optional?: boolean }[];
  depth_options: Record<string, number>;
  languages: string[];
  analyst_options: ProviderOption[];
  credential_requirements: Record<string, { required: string[]; optional: string[] }>;
}

export interface UserPreferencesResponse {
  ticker: string;
  output_language: string;
  analysts: string[];
  depth_key: string;
  llm_provider: string;
  quick_think_llm: string;
  deep_think_llm: string;
  provider_model_profiles: Record<string, { quick?: string; deep?: string }>;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  advanced_settings: Record<string, any>;
  data_vendors: Record<string, string>;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  preferences?: Record<string, any>;
  credentials: Record<string, CredentialStatus>;
}

