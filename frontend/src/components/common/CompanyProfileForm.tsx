import type { CompanyProfile, Sector } from '../../types/api';
import { SECTOR_OPTIONS } from '../../types/api';
import './CompanyProfileForm.css';

interface CompanyProfileFormProps {
  profile: CompanyProfile;
  onChange: (profile: CompanyProfile) => void;
}

const SAMPLE_PROFILE: Omit<CompanyProfile, 'financials'> = {
  entity_name: 'Bharat Steel Industries Ltd.',
  sector: 'manufacturing',
  sub_sector: 'Steel - Integrated',
  incorporation_year: 1998,
  promoter_group: 'Bharat Industrial Group',
  management_experience_years: 25,
  market_position: 'Mid-tier integrated steel manufacturer with presence in long products',
  geographic_diversification: 'Operations in Maharashtra and Karnataka with sales across western and southern India',
  product_diversification: 'TMT bars, structural steel, wire rods, and billets serving construction and infrastructure sectors',
};

export default function CompanyProfileForm({
  profile,
  onChange,
}: CompanyProfileFormProps) {
  const update = <K extends keyof CompanyProfile>(
    key: K,
    value: CompanyProfile[K]
  ) => {
    onChange({ ...profile, [key]: value });
  };

  const loadSample = () => {
    onChange({ ...profile, ...SAMPLE_PROFILE });
  };

  return (
    <div className="company-profile-form">
      <div className="company-profile-form__header">
        <h4 className="company-profile-form__title">Company Profile</h4>
        <button
          type="button"
          className="btn btn-accent btn-sm"
          onClick={loadSample}
        >
          Load Sample Data
        </button>
      </div>

      <div className="company-profile-form__grid">
        <div className="form-group company-profile-form__span-2">
          <label className="form-label">Entity Name *</label>
          <input
            className="form-input"
            type="text"
            value={profile.entity_name}
            onChange={(e) => update('entity_name', e.target.value)}
            placeholder="Company legal name"
            required
          />
        </div>

        <div className="form-group">
          <label className="form-label">Sector *</label>
          <select
            className="form-select"
            value={profile.sector}
            onChange={(e) => update('sector', e.target.value as Sector)}
            required
          >
            <option value="">Select sector</option>
            {SECTOR_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </div>

        <div className="form-group">
          <label className="form-label">Sub-Sector</label>
          <input
            className="form-input"
            type="text"
            value={profile.sub_sector}
            onChange={(e) => update('sub_sector', e.target.value)}
            placeholder="e.g. Steel - Integrated"
          />
        </div>

        <div className="form-group">
          <label className="form-label">Year of Incorporation</label>
          <input
            className="form-input"
            type="number"
            value={profile.incorporation_year || ''}
            onChange={(e) =>
              update(
                'incorporation_year',
                e.target.value ? parseInt(e.target.value, 10) : undefined
              )
            }
            placeholder="e.g. 1998"
          />
        </div>

        <div className="form-group">
          <label className="form-label">Promoter Group</label>
          <input
            className="form-input"
            type="text"
            value={profile.promoter_group || ''}
            onChange={(e) => update('promoter_group', e.target.value)}
            placeholder="Promoter group name"
          />
        </div>

        <div className="form-group">
          <label className="form-label">Management Experience (years)</label>
          <input
            className="form-input"
            type="number"
            value={profile.management_experience_years || ''}
            onChange={(e) =>
              update(
                'management_experience_years',
                e.target.value ? parseInt(e.target.value, 10) : undefined
              )
            }
            placeholder="e.g. 25"
          />
        </div>

        <div className="form-group company-profile-form__span-3">
          <label className="form-label">Market Position</label>
          <input
            className="form-input"
            type="text"
            value={profile.market_position || ''}
            onChange={(e) => update('market_position', e.target.value)}
            placeholder="Brief description of market positioning"
          />
        </div>

        <div className="form-group company-profile-form__span-3">
          <label className="form-label">Geographic Diversification</label>
          <input
            className="form-input"
            type="text"
            value={profile.geographic_diversification || ''}
            onChange={(e) =>
              update('geographic_diversification', e.target.value)
            }
            placeholder="Regions of operation and sales"
          />
        </div>

        <div className="form-group company-profile-form__span-3">
          <label className="form-label">Product Diversification</label>
          <input
            className="form-input"
            type="text"
            value={profile.product_diversification || ''}
            onChange={(e) =>
              update('product_diversification', e.target.value)
            }
            placeholder="Product lines and segments"
          />
        </div>
      </div>
    </div>
  );
}

export { SAMPLE_PROFILE };
