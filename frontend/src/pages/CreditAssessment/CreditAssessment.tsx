import { useState, useCallback } from 'react';
import Header from '../../components/Header/Header';
import Card from '../../components/common/Card';
import LoadingSpinner from '../../components/common/LoadingSpinner';
import CompanyProfileForm from '../../components/common/CompanyProfileForm';
import FinancialForm from '../../components/common/FinancialForm';
import MethodologyReferences from '../../components/common/MethodologyReferences';
import MarkdownRenderer from '../../components/common/MarkdownRenderer';
import DisclaimerBanner from '../../components/common/DisclaimerBanner';
import StatusBadge from '../../components/common/StatusBadge';
import { useApi } from '../../hooks/useApi';
import { apiClient } from '../../services/apiClient';
import type {
  CompanyProfile,
  Sector,
  CreditAssessmentResponse,
  CreditAssessmentRequest,
} from '../../types/api';
import { ASSESSMENT_TYPES, SECTOR_LABELS } from '../../types/api';
import './CreditAssessment.css';

const INITIAL_PROFILE: CompanyProfile = {
  entity_name: '',
  sector: 'manufacturing' as Sector,
  sub_sector: '',
  incorporation_year: undefined,
  promoter_group: '',
  management_experience_years: undefined,
  market_position: '',
  geographic_diversification: '',
  product_diversification: '',
  financials: [],
};

export default function CreditAssessment() {
  const [activeTab, setActiveTab] = useState<
    'profile' | 'financials' | 'context'
  >('profile');
  const [profile, setProfile] = useState<CompanyProfile>(INITIAL_PROFILE);
  const [assessmentType, setAssessmentType] = useState('initial_rating');
  const [additionalContext, setAdditionalContext] = useState('');

  const {
    data: assessment,
    loading,
    error,
    execute: generateAssessment,
  } = useApi<CreditAssessmentResponse, [CreditAssessmentRequest]>(
    useCallback(
      (req: CreditAssessmentRequest) =>
        apiClient.generateCreditAssessment(req),
      []
    )
  );

  const handleGenerate = () => {
    if (!profile.entity_name.trim()) {
      alert('Please provide the entity name.');
      setActiveTab('profile');
      return;
    }
    if (profile.financials.length === 0) {
      alert('Please add at least one fiscal year of financial data.');
      setActiveTab('financials');
      return;
    }

    generateAssessment({
      company_profile: profile,
      assessment_type: assessmentType,
      additional_context: additionalContext,
    });
  };

  const handlePrint = () => {
    window.print();
  };

  const tabs = [
    { key: 'profile' as const, label: 'Company Profile' },
    { key: 'financials' as const, label: 'Financial Data' },
    { key: 'context' as const, label: 'Additional Context' },
  ];

  return (
    <>
      <Header
        title="Credit Assessment"
        subtitle="Generate methodology-backed draft assessments"
      />
      <div className="credit-assessment">
        {/* Input Form */}
        <Card>
          <div className="credit-assessment__tabs">
            {tabs.map((tab) => (
              <button
                key={tab.key}
                type="button"
                className={`credit-assessment__tab ${activeTab === tab.key ? 'credit-assessment__tab--active' : ''}`}
                onClick={() => setActiveTab(tab.key)}
              >
                {tab.label}
                {tab.key === 'financials' &&
                  profile.financials.length > 0 && (
                    <span className="credit-assessment__tab-count">
                      {profile.financials.length}
                    </span>
                  )}
              </button>
            ))}
          </div>

          <div className="credit-assessment__tab-content">
            {activeTab === 'profile' && (
              <CompanyProfileForm profile={profile} onChange={setProfile} />
            )}

            {activeTab === 'financials' && (
              <FinancialForm
                financials={profile.financials}
                onChange={(financials) =>
                  setProfile((prev) => ({ ...prev, financials }))
                }
              />
            )}

            {activeTab === 'context' && (
              <div className="credit-assessment__context">
                <div className="form-group">
                  <label className="form-label">Assessment Type</label>
                  <select
                    className="form-select"
                    value={assessmentType}
                    onChange={(e) => setAssessmentType(e.target.value)}
                  >
                    {ASSESSMENT_TYPES.map((opt) => (
                      <option key={opt.value} value={opt.value}>
                        {opt.label}
                      </option>
                    ))}
                  </select>
                </div>
                <div className="form-group">
                  <label className="form-label">
                    Analyst Notes / Additional Context
                  </label>
                  <textarea
                    className="form-textarea"
                    value={additionalContext}
                    onChange={(e) => setAdditionalContext(e.target.value)}
                    placeholder="Provide any additional context, recent developments, or specific areas of focus for the assessment..."
                    rows={6}
                  />
                </div>
              </div>
            )}
          </div>

          <div className="credit-assessment__actions">
            <button
              className="btn btn-primary btn-lg"
              onClick={handleGenerate}
              disabled={loading}
            >
              {loading ? 'Generating Assessment...' : 'Generate Assessment'}
            </button>
          </div>
        </Card>

        {/* Loading */}
        {loading && (
          <LoadingSpinner
            size="lg"
            message="Generating credit assessment. This may take a moment as the system retrieves relevant methodology context and produces the analysis..."
          />
        )}

        {/* Error */}
        {error && (
          <Card>
            <div className="credit-assessment__error">
              <StatusBadge status="error" label="Generation Failed" />
              <p>{error}</p>
            </div>
          </Card>
        )}

        {/* Assessment Results */}
        {assessment && !loading && (
          <div className="credit-assessment__result">
            <Card>
              {/* Result Header */}
              <div className="credit-assessment__result-header">
                <div>
                  <h2 className="credit-assessment__entity-name">
                    {assessment.entity_name}
                  </h2>
                  <div className="credit-assessment__result-meta">
                    <span>
                      Sector:{' '}
                      {SECTOR_LABELS[assessment.sector as Sector] ??
                        assessment.sector}
                    </span>
                    <span className="credit-assessment__meta-sep">|</span>
                    <span>Date: {assessment.assessment_date}</span>
                    <span className="credit-assessment__meta-sep">|</span>
                    <span>ID: {assessment.correlation_id}</span>
                  </div>
                </div>
                <button
                  className="btn btn-secondary btn-sm"
                  onClick={handlePrint}
                >
                  Export / Print
                </button>
              </div>
            </Card>

            {/* Business Risk */}
            <Card title="Business Risk Assessment">
              <MarkdownRenderer content={assessment.business_risk_assessment} />
            </Card>

            {/* Financial Risk */}
            <Card title="Financial Risk Assessment">
              <MarkdownRenderer
                content={assessment.financial_risk_assessment}
              />
            </Card>

            {/* Strengths & Weaknesses */}
            <div className="credit-assessment__sw-grid">
              <Card title="Key Strengths">
                <ul className="credit-assessment__list credit-assessment__list--strengths">
                  {assessment.key_strengths.map((item, idx) => (
                    <li key={idx}>{item}</li>
                  ))}
                </ul>
              </Card>
              <Card title="Key Weaknesses">
                <ul className="credit-assessment__list credit-assessment__list--weaknesses">
                  {assessment.key_weaknesses.map((item, idx) => (
                    <li key={idx}>{item}</li>
                  ))}
                </ul>
              </Card>
            </div>

            {/* Outlook */}
            <Card title="Outlook Considerations">
              <MarkdownRenderer content={assessment.outlook_considerations} />
            </Card>

            {/* References */}
            <MethodologyReferences
              references={assessment.methodology_references}
            />

            {/* Disclaimer */}
            <DisclaimerBanner text={assessment.disclaimer} />
          </div>
        )}
      </div>
    </>
  );
}
