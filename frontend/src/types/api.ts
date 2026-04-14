/* ============================================================
   TypeScript interfaces matching the Rating Intelligence API
   ============================================================ */

/** Sector enum matching backend values */
export type Sector =
  | 'manufacturing'
  | 'financial'
  | 'infrastructure'
  | 'services'
  | 'real_estate'
  | 'power'
  | 'information_technology'
  | 'pharmaceuticals'
  | 'other';

export const SECTOR_OPTIONS: { value: Sector; label: string }[] = [
  { value: 'manufacturing', label: 'Manufacturing' },
  { value: 'financial', label: 'Financial Services' },
  { value: 'infrastructure', label: 'Infrastructure' },
  { value: 'services', label: 'Services' },
  { value: 'real_estate', label: 'Real Estate' },
  { value: 'power', label: 'Power' },
  { value: 'information_technology', label: 'Information Technology' },
  { value: 'pharmaceuticals', label: 'Pharmaceuticals' },
  { value: 'other', label: 'Other' },
];

/** Label mapping for display */
export const SECTOR_LABELS: Record<Sector, string> = {
  manufacturing: 'Manufacturing',
  financial: 'Financial Services',
  infrastructure: 'Infrastructure',
  services: 'Services',
  real_estate: 'Real Estate',
  power: 'Power',
  information_technology: 'Information Technology',
  pharmaceuticals: 'Pharmaceuticals',
  other: 'Other',
};

/* ---- Health ---- */

export interface LLMComponent {
  status: string;
  model: string;
  usage?: {
    prompt_tokens: number;
    completion_tokens: number;
    total_tokens: number;
    call_count: number;
    total_latency_ms: number;
    avg_latency_ms: number;
  };
}

export interface WeaviateComponent {
  status: string;
  collections: Record<string, number>;
}

export interface HealthResponse {
  status: string;
  components: {
    weaviate: WeaviateComponent;
    llm: LLMComponent;
  };
  version: string;
}

/* ---- Methodology Search ---- */

export interface MethodologySearchRequest {
  query: string;
  sector?: string | null;
  rating_scale_type?: string | null;
  limit?: number;
}

export interface SearchResultMetadata {
  source_document?: string;
  sector?: string;
  sub_sector?: string;
  section_title?: string;
  [key: string]: unknown;
}

export interface SearchResult {
  content: string;
  score: number;
  metadata: SearchResultMetadata;
}

export interface MethodologySearchResponse {
  query: string;
  results: SearchResult[];
  total_results: number;
  search_time_ms: number;
}

/* ---- Financial Data ---- */

export interface FinancialYear {
  fiscal_year: string;
  revenue: number;
  ebitda: number;
  ebitda_margin: number;
  pat: number;
  total_debt: number;
  tangible_net_worth: number;
  debt_to_equity: number;
  interest_coverage: number;
  current_ratio: number;
  roce: number;
  debt_to_ebitda: number;
  dscr: number;
  cash_and_equivalents: number;
}

/* ---- Company Profile ---- */

export interface CompanyProfile {
  entity_name: string;
  sector: Sector;
  sub_sector: string;
  incorporation_year?: number;
  promoter_group?: string;
  management_experience_years?: number;
  market_position?: string;
  geographic_diversification?: string;
  product_diversification?: string;
  financials: FinancialYear[];
}

/* ---- Credit Assessment ---- */

export interface CreditAssessmentRequest {
  company_profile: CompanyProfile;
  assessment_type: string;
  additional_context: string;
}

export interface MethodologyReference {
  source_document: string;
  section: string;
  content_excerpt: string;
  relevance_score: number;
}

export interface CreditAssessmentResponse {
  entity_name: string;
  sector: string;
  assessment_date: string;
  business_risk_assessment: string;
  financial_risk_assessment: string;
  key_strengths: string[];
  key_weaknesses: string[];
  outlook_considerations: string;
  methodology_references: MethodologyReference[];
  disclaimer: string;
  correlation_id: string;
}

/* ---- Peer Comparison ---- */

export interface PeerComparisonRequest {
  company_profile: CompanyProfile;
  peer_sector?: string | null;
  max_peers?: number;
}

export interface PeerComparisonResponse {
  entity_name: string;
  sector: string;
  comparison_date: string;
  analysis: string;
  peer_references: MethodologyReference[];
  methodology_references: MethodologyReference[];
  disclaimer: string;
}

/* ---- Surveillance Alerts ---- */

export interface SurveillanceAlertRequest {
  entity_name: string;
  sector: Sector;
  current_rating: string;
  financial_triggers: string[];
  latest_financials: FinancialYear;
  additional_context: string;
}

export interface SurveillanceAlertResponse {
  entity_name: string;
  current_rating: string;
  alert_date: string;
  alert_summary: string;
  triggers_identified: string[];
  methodology_references: MethodologyReference[];
  disclaimer: string;
}

/* ---- Assessment Types ---- */

export const ASSESSMENT_TYPES = [
  { value: 'initial_rating', label: 'Initial Rating' },
  { value: 'annual_surveillance', label: 'Annual Surveillance' },
  { value: 'rating_upgrade', label: 'Rating Upgrade Assessment' },
  { value: 'rating_downgrade', label: 'Rating Downgrade Assessment' },
  { value: 'outlook_revision', label: 'Outlook Revision' },
];
