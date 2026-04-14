import { useState, useCallback } from 'react';
import Header from '../../components/Header/Header';
import Card from '../../components/common/Card';
import LoadingSpinner from '../../components/common/LoadingSpinner';
import StatusBadge from '../../components/common/StatusBadge';
import CompanyProfileForm from '../../components/common/CompanyProfileForm';
import FinancialForm from '../../components/common/FinancialForm';
import MethodologyReferences from '../../components/common/MethodologyReferences';
import MarkdownRenderer from '../../components/common/MarkdownRenderer';
import DisclaimerBanner from '../../components/common/DisclaimerBanner';
import { useApi } from '../../hooks/useApi';
import { apiClient } from '../../services/apiClient';
import type {
  CompanyProfile,
  Sector,
  PeerComparisonRequest,
  PeerComparisonResponse,
} from '../../types/api';
import { SECTOR_OPTIONS, SECTOR_LABELS } from '../../types/api';
import './PeerComparison.css';

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

export default function PeerComparison() {
  const [profile, setProfile] = useState<CompanyProfile>(INITIAL_PROFILE);
  const [peerSector, setPeerSector] = useState<string>('');
  const [maxPeers, setMaxPeers] = useState(5);
  const [showFinancials, setShowFinancials] = useState(false);

  const {
    data: comparison,
    loading,
    error,
    execute: generateComparison,
  } = useApi<PeerComparisonResponse, [PeerComparisonRequest]>(
    useCallback(
      (req: PeerComparisonRequest) => apiClient.peerComparison(req),
      []
    )
  );

  const handleGenerate = () => {
    if (!profile.entity_name.trim()) {
      alert('Please provide the entity name.');
      return;
    }
    if (profile.financials.length === 0) {
      alert('Please add at least one fiscal year of financial data.');
      return;
    }

    generateComparison({
      company_profile: profile,
      peer_sector: peerSector || null,
      max_peers: maxPeers,
    });
  };

  return (
    <>
      <Header
        title="Peer Comparison"
        subtitle="Compare entity against sectoral peers"
      />
      <div className="peer-comparison">
        {/* Company Profile */}
        <Card>
          <CompanyProfileForm profile={profile} onChange={setProfile} />
        </Card>

        {/* Financial Data */}
        <Card
          title="Financial Data"
          headerAction={
            <button
              type="button"
              className="btn btn-secondary btn-sm"
              onClick={() => setShowFinancials(!showFinancials)}
            >
              {showFinancials ? 'Hide Financials' : 'Show / Edit Financials'}
            </button>
          }
        >
          {showFinancials ? (
            <FinancialForm
              financials={profile.financials}
              onChange={(financials) =>
                setProfile((prev) => ({ ...prev, financials }))
              }
            />
          ) : (
            <p className="peer-comparison__financial-summary">
              {profile.financials.length > 0
                ? `${profile.financials.length} fiscal year(s) loaded.`
                : 'No financial data. Expand this section to add data or load sample.'}
            </p>
          )}
        </Card>

        {/* Comparison Parameters */}
        <Card title="Comparison Parameters">
          <div className="peer-comparison__params">
            <div className="form-group">
              <label className="form-label">
                Peer Sector Override (optional)
              </label>
              <select
                className="form-select"
                value={peerSector}
                onChange={(e) => setPeerSector(e.target.value)}
              >
                <option value="">Same as entity sector</option>
                {SECTOR_OPTIONS.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
            </div>

            <div className="form-group">
              <label className="form-label">
                Maximum Peers: {maxPeers}
              </label>
              <input
                type="range"
                min={1}
                max={20}
                value={maxPeers}
                onChange={(e) => setMaxPeers(parseInt(e.target.value, 10))}
                className="peer-comparison__slider"
              />
            </div>
          </div>

          <div className="peer-comparison__actions">
            <button
              className="btn btn-primary btn-lg"
              onClick={handleGenerate}
              disabled={loading}
            >
              {loading ? 'Generating Comparison...' : 'Generate Peer Comparison'}
            </button>
          </div>
        </Card>

        {/* Loading */}
        {loading && (
          <LoadingSpinner
            size="lg"
            message="Generating peer comparison analysis. Retrieving sector benchmarks and methodology context..."
          />
        )}

        {/* Error */}
        {error && (
          <Card>
            <div className="peer-comparison__error">
              <StatusBadge status="error" label="Comparison Failed" />
              <p>{error}</p>
            </div>
          </Card>
        )}

        {/* Results */}
        {comparison && !loading && (
          <div className="peer-comparison__result">
            <Card>
              <div className="peer-comparison__result-header">
                <h2 className="peer-comparison__entity-name">
                  {comparison.entity_name}
                </h2>
                <div className="peer-comparison__result-meta">
                  <span>
                    Sector:{' '}
                    {SECTOR_LABELS[comparison.sector as Sector] ??
                      comparison.sector}
                  </span>
                  <span className="peer-comparison__meta-sep">|</span>
                  <span>Date: {comparison.comparison_date}</span>
                </div>
              </div>
            </Card>

            {/* Analysis */}
            <Card title="Comparative Analysis">
              <MarkdownRenderer content={comparison.analysis} />
            </Card>

            {/* Peer References */}
            {comparison.peer_references &&
              comparison.peer_references.length > 0 && (
                <MethodologyReferences
                  references={comparison.peer_references}
                  title="Peer References"
                />
              )}

            {/* Methodology References */}
            <MethodologyReferences
              references={comparison.methodology_references}
            />

            {/* Disclaimer */}
            <DisclaimerBanner text={comparison.disclaimer} />
          </div>
        )}
      </div>
    </>
  );
}
