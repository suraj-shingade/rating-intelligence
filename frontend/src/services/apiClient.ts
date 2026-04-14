/* ============================================================
   API Client -- Centralized HTTP layer for the Rating
   Intelligence backend.
   ============================================================ */

import type {
  HealthResponse,
  MethodologySearchRequest,
  MethodologySearchResponse,
  CreditAssessmentRequest,
  CreditAssessmentResponse,
  PeerComparisonRequest,
  PeerComparisonResponse,
  SurveillanceAlertRequest,
  SurveillanceAlertResponse,
} from '../types/api';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? '';

class ApiError extends Error {
  public readonly status: number;
  public readonly detail: string;

  constructor(status: number, detail: string) {
    super(`API Error ${status}: ${detail}`);
    this.name = 'ApiError';
    this.status = status;
    this.detail = detail;
  }
}

async function request<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${API_BASE_URL}${endpoint}`;
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string> | undefined),
  };

  const response = await fetch(url, { ...options, headers });

  if (!response.ok) {
    let detail = response.statusText;
    try {
      const body = await response.json();
      detail = body.detail ?? body.message ?? JSON.stringify(body);
    } catch {
      /* use statusText fallback */
    }
    throw new ApiError(response.status, detail);
  }

  return response.json() as Promise<T>;
}

/* ---- Public API surface ---- */

export const apiClient = {
  /** Health check */
  getHealth(): Promise<HealthResponse> {
    return request<HealthResponse>('/api/v1/health');
  },

  /** Semantic methodology search */
  searchMethodology(
    body: MethodologySearchRequest
  ): Promise<MethodologySearchResponse> {
    return request<MethodologySearchResponse>('/api/v1/search/methodology', {
      method: 'POST',
      body: JSON.stringify(body),
    });
  },

  /** Generate a credit assessment draft */
  generateCreditAssessment(
    body: CreditAssessmentRequest
  ): Promise<CreditAssessmentResponse> {
    return request<CreditAssessmentResponse>(
      '/api/v1/analysis/credit-assessment',
      {
        method: 'POST',
        body: JSON.stringify(body),
      }
    );
  },

  /** Peer comparison analysis */
  peerComparison(
    body: PeerComparisonRequest
  ): Promise<PeerComparisonResponse> {
    return request<PeerComparisonResponse>('/api/v1/analysis/peer-comparison', {
      method: 'POST',
      body: JSON.stringify(body),
    });
  },

  /** Surveillance alert memorandum */
  surveillanceAlert(
    body: SurveillanceAlertRequest
  ): Promise<SurveillanceAlertResponse> {
    return request<SurveillanceAlertResponse>(
      '/api/v1/surveillance/alerts',
      {
        method: 'POST',
        body: JSON.stringify(body),
      }
    );
  },
};

export { ApiError };
