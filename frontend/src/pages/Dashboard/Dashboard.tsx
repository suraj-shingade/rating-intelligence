import { useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import Header from '../../components/Header/Header';
import Card from '../../components/common/Card';
import StatusBadge from '../../components/common/StatusBadge';
import LoadingSpinner from '../../components/common/LoadingSpinner';
import { useApi } from '../../hooks/useApi';
import { apiClient } from '../../services/apiClient';
import type { HealthResponse } from '../../types/api';
import './Dashboard.css';

export default function Dashboard() {
  const navigate = useNavigate();
  const {
    data: health,
    loading,
    error,
    execute: fetchHealth,
  } = useApi<HealthResponse>(useCallback(() => apiClient.getHealth(), []));

  useEffect(() => {
    fetchHealth();
  }, [fetchHealth]);

  const collections = health?.components?.weaviate?.collections ?? {};
  const totalDocs = Object.values(collections).reduce((sum, count) => sum + count, 0);

  const quickActions = [
    {
      title: 'Methodology Search',
      description:
        'Search across CRISIL rating methodologies using semantic intelligence',
      path: '/search',
    },
    {
      title: 'Credit Assessment',
      description:
        'Generate draft credit assessments with methodology-backed analysis',
      path: '/assessment',
    },
    {
      title: 'Surveillance Alerts',
      description:
        'Produce surveillance alert memorandums for monitored entities',
      path: '/surveillance',
    },
    {
      title: 'Peer Comparison',
      description:
        'Compare entity financials against sectoral peers with AI analysis',
      path: '/peer-comparison',
    },
  ];

  return (
    <>
      <Header title="Dashboard" subtitle="System Overview" />
      <div className="dashboard">
        {/* System Health */}
        <section className="dashboard__section">
          <h2 className="dashboard__section-title">System Health</h2>

          {loading && <LoadingSpinner message="Checking system health..." />}
          {error && (
            <Card>
              <div className="dashboard__error">
                <StatusBadge status="error" label="Connection Error" />
                <p className="dashboard__error-text">{error}</p>
                <button
                  className="btn btn-secondary btn-sm"
                  onClick={() => fetchHealth()}
                >
                  Retry
                </button>
              </div>
            </Card>
          )}

          {health && !loading && (
            <div className="dashboard__health-grid">
              <Card title="Weaviate Vector Store">
                <div className="dashboard__status-row">
                  <StatusBadge
                    status={health.components.weaviate.status === 'connected' ? 'success' : 'error'}
                    label={health.components.weaviate.status}
                  />
                </div>
                <div className="dashboard__collections">
                  {Object.entries(collections).map(([name, count]) => (
                    <div className="dashboard__collection-item" key={name}>
                      <span className="dashboard__collection-name">
                        {name}
                      </span>
                      <span className="dashboard__collection-count">
                        {count.toLocaleString()} records
                      </span>
                    </div>
                  ))}
                </div>
              </Card>

              <Card title="LLM Service">
                <div className="dashboard__status-row">
                  <StatusBadge
                    status={
                      health.components.llm.status === 'connected' ? 'success' : 'warning'
                    }
                    label={health.components.llm.status}
                  />
                </div>
                <p className="dashboard__meta">
                  Model: {health.components.llm.model}
                </p>
                {health.components.llm.usage && (
                  <p className="dashboard__meta">
                    API Calls: {health.components.llm.usage.call_count} | Avg Latency: {health.components.llm.usage.avg_latency_ms.toFixed(0)}ms
                  </p>
                )}
              </Card>

              <Card title="Knowledge Base">
                <div className="dashboard__metric">
                  <span className="dashboard__metric-value">
                    {totalDocs.toLocaleString()}
                  </span>
                  <span className="dashboard__metric-label">
                    Total Documents Indexed
                  </span>
                </div>
                <div className="dashboard__metric">
                  <span className="dashboard__metric-value">
                    {Object.keys(collections).length}
                  </span>
                  <span className="dashboard__metric-label">
                    Active Collections
                  </span>
                </div>
              </Card>
            </div>
          )}
        </section>

        {/* Quick Actions */}
        <section className="dashboard__section">
          <h2 className="dashboard__section-title">Quick Actions</h2>
          <div className="dashboard__actions-grid">
            {quickActions.map((action) => (
              <button
                key={action.path}
                className="dashboard__action-card"
                onClick={() => navigate(action.path)}
              >
                <h3 className="dashboard__action-title">{action.title}</h3>
                <p className="dashboard__action-desc">{action.description}</p>
                <span className="dashboard__action-link">Open &rarr;</span>
              </button>
            ))}
          </div>
        </section>

        {/* Recent Activity Placeholder */}
        <section className="dashboard__section">
          <h2 className="dashboard__section-title">Recent Activity</h2>
          <Card>
            <div className="dashboard__placeholder">
              <p>
                Activity log will display recent searches, assessments, and
                alerts generated during this session.
              </p>
            </div>
          </Card>
        </section>
      </div>
    </>
  );
}
