// ── Core types matching the backend API ──

export interface Prospect {
  id: string;
  first_name: string;
  last_name: string;
  email?: string;
  phone?: string;
  title?: string;
  company?: string;
  linkedin_url?: string;
  status: ProspectStatus;
  sentiment: string;
  lead_score: number;
  tags: string[];
  notes?: string;
  created_at?: string;
  updated_at?: string;
}

export type ProspectStatus =
  | "new"
  | "researching"
  | "qualified"
  | "contacted"
  | "engaged"
  | "opportunity"
  | "customer"
  | "churned"
  | "disqualified";

export interface Deal {
  id: string;
  title: string;
  prospect_id: string;
  company?: string;
  stage: DealStage;
  value: number;
  currency: string;
  probability: number;
  expected_close_date?: string;
  competitors: string[];
  loss_reason?: string;
  notes?: string;
  created_at?: string;
  updated_at?: string;
  closed_at?: string;
}

export type DealStage =
  | "prospecting"
  | "qualification"
  | "discovery"
  | "proposal"
  | "negotiation"
  | "closed_won"
  | "closed_lost";

export interface Interaction {
  id: string;
  prospect_id: string;
  deal_id?: string;
  channel: string;
  direction: "inbound" | "outbound";
  subject?: string;
  content: string;
  sentiment?: string;
  opened: boolean;
  clicked: boolean;
  replied: boolean;
  created_at?: string;
}

export interface PipelineSummary {
  total_pipeline_value: number;
  total_deals: number;
  average_deal_size: number;
  stages: Record<string, { count: number; value: number; pct_of_pipeline: number }>;
  health: string;
}

export interface ActivityMetrics {
  period_days: number;
  total_interactions: number;
  by_channel: Record<string, number>;
  by_direction: Record<string, number>;
  outbound_count: number;
  reply_count: number;
  open_count: number;
  reply_rate: number;
  open_rate: number;
  daily_average: number;
}

export interface FunnelData {
  funnel: { stage: string; count: number }[];
  total_prospects: number;
  total_deals: number;
  win_rate: number;
  prospect_to_deal_rate: number;
}

export interface ForecastData {
  forecast: {
    weighted_total: number;
    unweighted_total: number;
    deal_count: number;
    best_case: number;
    expected: number;
    worst_case: number;
  };
  confidence: string;
  confidence_percentage: number;
  summary: string;
}

export interface PerformanceReport {
  period_days: number;
  pipeline: PipelineSummary;
  activity: ActivityMetrics;
  funnel: FunnelData;
  scores: Record<string, number>;
  overall_score: number;
  grade: string;
}

export interface Integration {
  name: string;
  category: string;
  connected: boolean;
}
