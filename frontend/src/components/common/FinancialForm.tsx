import { useState } from 'react';
import type { FinancialYear } from '../../types/api';
import './FinancialForm.css';

interface FinancialFormProps {
  financials: FinancialYear[];
  onChange: (financials: FinancialYear[]) => void;
}

const EMPTY_FINANCIAL_YEAR: FinancialYear = {
  fiscal_year: '',
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

const SAMPLE_FINANCIALS: FinancialYear[] = [
  {
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
  {
    fiscal_year: 'FY2023',
    revenue: 3800.0,
    ebitda: 570.0,
    ebitda_margin: 15.0,
    pat: 280.0,
    total_debt: 2000.0,
    tangible_net_worth: 1900.0,
    debt_to_equity: 1.05,
    interest_coverage: 3.2,
    current_ratio: 1.2,
    roce: 12.8,
    debt_to_ebitda: 3.51,
    dscr: 1.3,
    cash_and_equivalents: 250.0,
  },
  {
    fiscal_year: 'FY2022',
    revenue: 3200.0,
    ebitda: 448.0,
    ebitda_margin: 14.0,
    pat: 210.0,
    total_debt: 2200.0,
    tangible_net_worth: 1700.0,
    debt_to_equity: 1.29,
    interest_coverage: 2.8,
    current_ratio: 1.1,
    roce: 11.5,
    debt_to_ebitda: 4.91,
    dscr: 1.15,
    cash_and_equivalents: 180.0,
  },
];

const FIELD_CONFIG: {
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

export default function FinancialForm({
  financials,
  onChange,
}: FinancialFormProps) {
  const [expandedYear, setExpandedYear] = useState<number | null>(
    financials.length > 0 ? 0 : null
  );

  const addYear = () => {
    const updated = [...financials, { ...EMPTY_FINANCIAL_YEAR }];
    onChange(updated);
    setExpandedYear(updated.length - 1);
  };

  const removeYear = (index: number) => {
    const updated = financials.filter((_, i) => i !== index);
    onChange(updated);
    if (expandedYear === index) {
      setExpandedYear(updated.length > 0 ? 0 : null);
    } else if (expandedYear !== null && expandedYear > index) {
      setExpandedYear(expandedYear - 1);
    }
  };

  const updateField = (
    index: number,
    key: keyof FinancialYear,
    rawValue: string
  ) => {
    const updated = [...financials];
    const entry = { ...updated[index] };
    if (key === 'fiscal_year') {
      entry[key] = rawValue;
    } else {
      entry[key] = rawValue === '' ? 0 : parseFloat(rawValue);
    }
    updated[index] = entry;
    onChange(updated);
  };

  const loadSampleData = () => {
    onChange(SAMPLE_FINANCIALS.map((fy) => ({ ...fy })));
    setExpandedYear(0);
  };

  return (
    <div className="financial-form">
      <div className="financial-form__actions">
        <button
          type="button"
          className="btn btn-secondary btn-sm"
          onClick={addYear}
        >
          + Add Fiscal Year
        </button>
        <button
          type="button"
          className="btn btn-accent btn-sm"
          onClick={loadSampleData}
        >
          Load Sample Data
        </button>
      </div>

      {financials.length === 0 && (
        <p className="financial-form__empty">
          No financial data added. Click "Add Fiscal Year" or "Load Sample Data"
          to begin.
        </p>
      )}

      {financials.map((fy, index) => (
        <div className="financial-form__year" key={index}>
          <button
            type="button"
            className="financial-form__year-header"
            onClick={() =>
              setExpandedYear(expandedYear === index ? null : index)
            }
          >
            <span className="financial-form__year-label">
              {fy.fiscal_year || `Year ${index + 1}`}
              {fy.revenue > 0 && (
                <span className="financial-form__year-summary">
                  Revenue: {fy.revenue.toLocaleString()} Cr | EBITDA:{' '}
                  {fy.ebitda.toLocaleString()} Cr
                </span>
              )}
            </span>
            <span className="financial-form__year-actions">
              <span
                className="financial-form__remove"
                onClick={(e) => {
                  e.stopPropagation();
                  removeYear(index);
                }}
                role="button"
                tabIndex={0}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    e.stopPropagation();
                    removeYear(index);
                  }
                }}
                title="Remove this fiscal year"
              >
                Remove
              </span>
              <span
                className={`financial-form__chevron ${expandedYear === index ? 'financial-form__chevron--open' : ''}`}
              >
                &#9662;
              </span>
            </span>
          </button>

          {expandedYear === index && (
            <div className="financial-form__year-body">
              <div className="financial-form__grid">
                {FIELD_CONFIG.map((field) => (
                  <div className="form-group" key={field.key}>
                    <label className="form-label">
                      {field.label}
                      {field.suffix && (
                        <span className="financial-form__suffix">
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
                          ? (fy[field.key] as string)
                          : (fy[field.key] as number) || ''
                      }
                      onChange={(e) =>
                        updateField(index, field.key, e.target.value)
                      }
                      placeholder={field.label}
                    />
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

export { SAMPLE_FINANCIALS };
