import { useState, useCallback } from 'react';
import Header from '../../components/Header/Header';
import Card from '../../components/common/Card';
import LoadingSpinner from '../../components/common/LoadingSpinner';
import StatusBadge from '../../components/common/StatusBadge';
import MethodologyReferences from '../../components/common/MethodologyReferences';
import MarkdownRenderer from '../../components/common/MarkdownRenderer';
import DisclaimerBanner from '../../components/common/DisclaimerBanner';
import { useApi } from '../../hooks/useApi';
import { apiClient } from '../../services/apiClient';
import type {
  Sector,
  FinancialYear,
  SurveillanceAlertRequest,
  SurveillanceAlertResponse,
} from '../../types/api';
import { SECTOR_OPTIONS } from '../../types/api';
import './SurveillanceAlerts.css';

const EMPTY_FINANCIALS: FinancialYear = {
  fiscal_year: 'FY2024',
  revenue: 0,
  ebitda: 0,
  ebitda_margin: 0,
  pat: 0,
  total_debt: 0,
  tangible_net_worth: 0,
  debt_to_equity: 0,
  interest_coverage: 0,
  current_ratio: 0,
  roce: 0,
  debt_to_ebitda: 0,
  dscr: 0,
  cash_and_equivalents: 0,
};

const SAMPLE_ALERT_DATA = {
  entity_name: 'Bharat Steel Industries Ltd.',
  sector: 'manufacturing' as Sector,
  current_rating: 'CRISIL BBB+/Stable',
  financial_triggers: [
    'Debt-to-EBITDA exceeded 3.5x threshold',
    'EBITDA margin declined below 14% for consecutive quarters',
    'Working capital cycle elongated beyond 90 days',
  ],
  latest_financials: {
    fiscal_year: 'FY2024',
    revenue: 4250.0,
    ebitda: 680.0,
    ebitda_margin: 16.0,
    pat: 340.0,
    total_debt: 1800.0,
    tangible_net_worth: 2100.0,
    debt_to_equity: 0.86,
    interest_coverage: 3.8,
    current_ratio: 1.35,
    roce: 14.2,
    debt_to_ebitda: 2.65,
    dscr: 1.45,
    cash_and_equivalents: 320.0,
  },
  additional_context:
    'Entity has undertaken a capacity expansion project with expected commissioning in Q2 FY2025. Raw material costs have increased 12% YoY.',
};

const FINANCIAL_FIELDS: {
  key: keyof FinancialYear;
  label: string;
  type: 'text' | 'number';
  step?: string;
  suffix?: string;
}[] = [
  { key: 'fiscal_year', label: 'Fiscal Year', type: 'text' },
  { key: 'revenue', label: 'Revenue', type: 'number', suffix: 'Cr' },
  { key: 'ebitda', label: 'EBITDA', type: 'number', suffix: 'Cr' },
  { key: 'ebitda_margin', label: 'EBITDA Margin', type: 'number', step: '0.1', suffix: '%' },
  { key: 'pat', label: 'PAT', type: 'number', suffix: 'Cr' },
  { key: 'total_debt', label: 'Total Debt', type: 'number', suffix: 'Cr' },
  { key: 'tangible_net_worth', label: 'Tangible Net Worth', type: 'number', suffix: 'Cr' },
  { key: 'debt_to_equity', label: 'Debt/Equity', type: 'number', step: '0.01', suffix: 'x' },
  { key: 'interest_coverage', label: 'Interest Coverage', type: 'number', step: '0.1', suffix: 'x' },
  { key: 'current_ratio', label: 'Current Ratio', type: 'number', step: '0.01', suffix: 'x' },
  { key: 'roce', label: 'ROCE', type: 'number', step: '0.1', suffix: '%' },
  { key: 'debt_to_ebitda', label: 'Debt/EBITDA', type: 'number', step: '0.01', suffix: 'x' },
  { key: 'dscr', label: 'DSCR', type: 'number', step: '0.01', suffix: 'x' },
  { key: 'cash_and_equivalents', label: 'Cash & Equivalents', type: 'number', suffix: 'Cr' },
];

export default function SurveillanceAlerts() {
  const [entityName, setEntityName] = useState('');
  const [sector, setSector] = useState<Sector>('manufacturing');
  const [currentRating, setCurrentRating] = useState('');
  const [triggers, setTriggers] = useState<string[]>(['']);
  const [financials, setFinancials] = useState<FinancialYear>({
    ...EMPTY_FINANCIALS,
  });
  const [additionalContext, setAdditionalContext] = useState('');

  const {
    data: alertData,
    loading,
    error,
    execute: generateAlert,
  } = useApi<SurveillanceAlertResponse, [SurveillanceAlertRequest]>(
    useCallback(
      (req: SurveillanceAlertRequest) => apiClient.surveillanceAlert(req),
      []
    )
  );

  const addTrigger = () => setTriggers((prev) => [...prev, '']);
  const removeTrigger = (index: number) =>
    setTriggers((prev) => prev.filter((_, i) => i !== index));
  const updateTrigger = (index: number, value: string) =>
    setTriggers((prev) => prev.map((t, i) => (i === index ? value : t)));

  const updateFinancial = (key: keyof FinancialYear, rawValue: string) => {
    setFinancials((prev) => {
      const updated = { ...prev };
      if (key === 'fiscal_year') {
        updated[key] = rawValue;
      } else {
        updated[key] = rawValue === '' ? 0 : parseFloat(rawValue);
      }
      return updated;
    });
  };

  const loadSample = () => {
    setEntityName(SAMPLE_ALERT_DATA.entity_name);
    setSector(SAMPLE_ALERT_DATA.sector);
    setCurrentRating(SAMPLE_ALERT_DATA.current_rating);
    setTriggers([...SAMPLE_ALERT_DATA.financial_triggers]);
    setFinancials({ ...SAMPLE_ALERT_DATA.latest_financials });
    setAdditionalContext(SAMPLE_ALERT_DATA.additional_context);
  };

  const handleGenerate = () => {
    if (!entityName.trim()) {
      window.alert('Please provide the entity name.');
      return;
    }
    const validTriggers = triggers.filter((t) => t.trim());
    if (validTriggers.length === 0) {
      window.alert('Please provide at least one financial trigger.');
      return;
    }

    generateAlert({
      entity_name: entityName,
      sector,
      current_rating: currentRating,
      financial_triggers: validTriggers,
      latest_financials: financials,
      additional_context: additionalContext,
    });
  };

  return (
    <>
      <Header
        title="Surveillance Alerts"
        subtitle="Generate surveillance alert memorandums"
      />
      <div className="surveillance">
        {/* Input Form */}
        <Card
          title="Alert Parameters"
          headerAction={
            <button
              type="button"
              className="btn btn-accent btn-sm"
              onClick={loadSample}
            >
              Load Sample Data
            </button>
          }
        >
          <div className="surveillance__form-grid">
            <div className="form-group surveillance__span-2">
              <label className="form-label">Entity Name *</label>
              <input
                className="form-input"
                type="text"
                value={entityName}
                onChange={(e) => setEntityName(e.target.value)}
                placeholder="Company legal name"
              />
            </div>

            <div className="form-group">
              <label className="form-label">Sector *</label>
              <select
                className="form-select"
                value={sector}
                onChange={(e) => setSector(e.target.value as Sector)}
              >
                {SECTOR_OPTIONS.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
            </div>

            <div className="form-group">
              <label className="form-label">Current Rating</label>
              <input
                className="form-input"
                type="text"
                value={currentRating}
                onChange={(e) => setCurrentRating(e.target.value)}
                placeholder="e.g. CRISIL BBB+/Stable"
              />
            </div>
          </div>

          {/* Financial Triggers */}
          <div className="surveillance__triggers">
            <div className="surveillance__triggers-header">
              <label className="form-label">Financial Triggers *</label>
              <button
                type="button"
                className="btn btn-secondary btn-sm"
                onClick={addTrigger}
              >
                + Add Trigger
              </button>
            </div>
            {triggers.map((trigger, index) => (
              <div className="surveillance__trigger-row" key={index}>
                <input
                  className="form-input"
                  type="text"
                  value={trigger}
                  onChange={(e) => updateTrigger(index, e.target.value)}
                  placeholder="Describe the financial trigger..."
                />
                {triggers.length > 1 && (
                  <button
                    type="button"
                    className="surveillance__trigger-remove"
                    onClick={() => removeTrigger(index)}
                    title="Remove trigger"
                  >
                    X
                  </button>
                )}
              </div>
            ))}
          </div>

          {/* Latest Financials */}
          <div className="surveillance__financials-section">
            <h4 className="surveillance__sub-title">Latest Financials</h4>
            <div className="surveillance__financials-grid">
              {FINANCIAL_FIELDS.map((field) => (
                <div className="form-group" key={field.key}>
                  <label className="form-label">
                    {field.label}
                    {field.suffix && (
                      <span className="surveillance__suffix">
                        {' '}
                        ({field.suffix})
                      </span>
                    )}
                  </label>
                  <input
                    className="form-input"
                    type={field.type}
                    step={field.step}
                    value={
                      field.key === 'fiscal_year'
                        ? (financials[field.key] as string)
                        : (financials[field.key] as number) || ''
                    }
                    onChange={(e) =>
                      updateFinancial(field.key, e.target.value)
                    }
                    placeholder={field.label}
                  />
                </div>
              ))}
            </div>
          </div>

          {/* Additional Context */}
          <div className="form-group surveillance__context-group">
            <label className="form-label">Additional Context</label>
            <textarea
              className="form-textarea"
              value={additionalContext}
              onChange={(e) => setAdditionalContext(e.target.value)}
              placeholder="Recent developments, market conditions, or specific concerns..."
              rows={4}
            />
          </div>

          <div className="surveillance__actions">
            <button
              className="btn btn-primary btn-lg"
              onClick={handleGenerate}
              disabled={loading}
            >
              {loading ? 'Generating Alert...' : 'Generate Alert'}
            </button>
          </div>
        </Card>

        {/* Loading */}
        {loading && (
          <LoadingSpinner
            size="lg"
            message="Generating surveillance alert memorandum..."
          />
        )}

        {/* Error */}
        {error && (
          <Card>
            <div className="surveillance__error">
              <StatusBadge status="error" label="Generation Failed" />
              <p>{error}</p>
            </div>
          </Card>
        )}

        {/* Results */}
        {alertData && !loading && (
          <div className="surveillance__result">
            <Card>
              <div className="surveillance__result-header">
                <h2 className="surveillance__result-entity">
                  {alertData.entity_name}
                </h2>
                <div className="surveillance__result-meta">
                  <StatusBadge status="warning" label={alertData.current_rating} />
                  <span className="surveillance__result-date">
                    Alert Date: {alertData.alert_date}
                  </span>
                </div>
              </div>
            </Card>

            {/* Alert Summary */}
            <Card title="Alert Summary">
              <MarkdownRenderer content={alertData.alert_summary} />
            </Card>

            {/* Triggers Identified */}
            {alertData.triggers_identified && alertData.triggers_identified.length > 0 && (
              <Card title="Triggers Identified">
                <ul className="surveillance__triggers-list">
                  {alertData.triggers_identified.map((trigger, idx) => (
                    <li key={idx} className="surveillance__trigger-item">
                      <span className="surveillance__trigger-indicator" />
                      {trigger}
                    </li>
                  ))}
                </ul>
              </Card>
            )}

            {/* References */}
            <MethodologyReferences
              references={alertData.methodology_references}
            />

            {/* Disclaimer */}
            <DisclaimerBanner text={alertData.disclaimer} />
          </div>
        )}
      </div>
    </>
  );
}
