export interface FinancialProjections {
  revenue_projections: number[];
  ebitda_margins: number[];
  capex_percent: number;
  nwc_change_percent: number;
  tax_rate: number;
  wacc: number;
  terminal_growth_rate: number;
  depreciation_percent: number;
}

export interface ValuationRequest {
  company_name: string;
  description?: string;
  sector?: string;
  revenue?: number;
  ebitda?: number;
  comparable_tickers?: string[];
  financial_projections?: FinancialProjections;
  last_round_valuation?: number;
  last_round_date?: string;
  index_ticker?: string;
}

export interface EstimatedFinancials {
  estimated_revenue?: number;
  estimated_ebitda?: number;
  revenue_source?: string;
  confidence?: string;
  reasoning?: string;
}

export interface EstimatedProjections {
  estimated_growth_rates: number[];
  estimated_ebitda_margins: number[];
  estimated_wacc: number;
  estimated_terminal_growth_rate: number;
  source: string;
  confidence: string;
  reasoning: string;
}

export interface EstimatedLastRound {
  estimated_valuation: number;
  estimated_date: string;
  source: string;
  confidence: string;
  reasoning: string;
}

export interface ResearchSource {
  title: string;
  url: string;
}

export interface EnrichedInput {
  sector: string;
  sub_sector?: string;
  comparable_tickers: string[];
  applicable_methods: string[];
  estimated_financials?: EstimatedFinancials;
  estimated_projections?: EstimatedProjections;
  estimated_last_round?: EstimatedLastRound;
  research_sources?: ResearchSource[];
  enrichment_notes?: string;
}

export interface CompanyFinancials {
  ticker: string;
  name?: string;
  market_cap?: number;
  enterprise_value?: number;
  revenue?: number;
  ebitda?: number;
  ev_to_revenue?: number;
  ev_to_ebitda?: number;
  sector?: string;
  data_source_url?: string;
  fetched_at?: string;
  data_source?: string;
}

export interface IndexData {
  ticker: string;
  price_at_round?: number;
  price_current?: number;
  return_since_round?: number;
}

export interface CompSelectionScore {
  ticker: string;
  name?: string;
  included: boolean;
  sector_score: number;
  size_proximity_score: number;
  data_quality_score: number;
  composite_score: number;
  exclusion_reason?: string;
}

export interface CompsResult {
  method: string;
  enterprise_value: number;
  ev_to_revenue_median: number;
  ev_to_revenue_mean: number;
  ev_to_ebitda_median?: number;
  ev_to_ebitda_mean?: number;
  comparable_count: number;
  comparables_used: string[];
  warnings: string[];
  comp_selection_scores?: CompSelectionScore[];
  selection_criteria?: Record<string, unknown>;
}

export interface SensitivityCell {
  wacc: number;
  terminal_growth_rate: number;
  enterprise_value: number;
}

export interface DCFResult {
  method: string;
  enterprise_value: number;
  projected_fcfs: number[];
  terminal_value: number;
  discount_rate: number;
  terminal_growth_rate: number;
  warnings: string[];
  sensitivity_table?: SensitivityCell[];
}

export interface LastRoundResult {
  method: string;
  enterprise_value: number;
  last_round_valuation: number;
  index_return?: number;
  adjustment_factor: number;
  months_since_round?: number;
  warnings: string[];
}

export interface MethodologyWeight {
  method: string;
  weight: number;
  rationale: string;
}

export interface BlendedValuation {
  fair_value: number;
  fair_value_range: [number, number];
  methodology_weights: MethodologyWeight[];
  comps_result?: CompsResult;
  dcf_result?: DCFResult;
  last_round_result?: LastRoundResult;
}

export interface PipelineStep {
  step_name: string;
  status: string;
  started_at?: string;
  completed_at?: string;
  duration_ms?: number;
  error?: string;
}

export interface LLMCallLog {
  step_name: string;
  model: string;
  system_prompt: string;
  user_prompt: string;
  response: string;
  tokens_used?: number;
  duration_ms?: number;
  timestamp: string;
}

export interface ValuationReport {
  id?: string;
  company_name: string;
  request_summary: Record<string, unknown>;
  enriched_input?: Record<string, unknown>;
  market_data_summary?: Record<string, unknown>;
  blended_valuation?: BlendedValuation;
  narrative?: string;
  error?: string;
  missing_data?: string[];
  pipeline_steps: PipelineStep[];
  llm_call_logs: LLMCallLog[];
  created_at: string;
  assumptions: Record<string, unknown>;
}

export interface ValuationSummary {
  id: string;
  company_name: string;
  fair_value?: number;
  created_at?: string;
}
