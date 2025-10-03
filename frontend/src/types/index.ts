export interface Incentive {
  id: number;
  incentive_project_id?: string;
  project_id?: string;
  incentive_program?: string;
  title: string;
  description?: string;
  ai_description?: string;
  ai_description_structured?: {
    objective?: string;
    sectors?: string[];
    regions?: string[];
    activities?: string[];
    funding_type?: string;
    requirements?: string[];
    focus_areas?: string[];
  };
  eligibility_criteria?: Record<string, any>;
  document_urls?: any[];
  date_publication?: string;
  date_start?: string;
  date_end?: string;
  total_budget?: number;
  source_link?: string;
  gcs_document_urls?: string[];
  status?: string;
  created_at?: string;
  updated_at?: string;
}

export interface Company {
  id: number;
  company_name: string;
  cae_primary_label?: string;
  trade_description_native?: string;
  website?: string;
  created_at?: string;
}

export interface Match {
  id: number;
  incentive_id: number;
  company_id: number;
  score: number;
  rank_position: number;
  reasoning?: {
    strategic_fit?: number;
    quality?: number;
    execution_capacity?: number;
    rationale?: string;
  };
  created_at?: string;
  incentive?: Incentive;
  company?: Company;
}

export interface SuggestedAction {
  label: string;
  action_type: "view_incentive" | "view_company" | "search" | "question";
  action_data?: Record<string, any>;
}

export interface ChatMetadata {
  tools_used: string[];
  data_count?: number;
  entity_type?: "incentives" | "companies" | "matches" | "general";
  suggested_actions: SuggestedAction[];
  sources: string[];
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  timestamp?: string;
  metadata?: ChatMetadata;
}
