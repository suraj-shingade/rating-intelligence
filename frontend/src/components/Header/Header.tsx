import { useState, useEffect, useCallback } from 'react';
import { apiClient } from '../../services/apiClient';
import StatusBadge from '../common/StatusBadge';
import './Header.css';

interface HeaderProps {
  title: string;
  subtitle?: string;
}

export default function Header({ title, subtitle }: HeaderProps) {
  const [systemStatus, setSystemStatus] = useState<
    'connected' | 'degraded' | 'offline'
  >('offline');

  const checkHealth = useCallback(async () => {
    try {
      const health = await apiClient.getHealth();
      const weaviateOk = health.components.weaviate.status === 'connected';
      const llmOk = health.components.llm.status === 'connected';
      if (weaviateOk && llmOk) {
        setSystemStatus('connected');
      } else {
        setSystemStatus('degraded');
      }
    } catch {
      setSystemStatus('offline');
    }
  }, []);

  useEffect(() => {
    checkHealth();
    const interval = setInterval(checkHealth, 30000);
    return () => clearInterval(interval);
  }, [checkHealth]);

  const statusMap = {
    connected: { status: 'success' as const, label: 'System Online' },
    degraded: { status: 'warning' as const, label: 'Degraded' },
    offline: { status: 'error' as const, label: 'Offline' },
  };

  const { status, label } = statusMap[systemStatus];

  return (
    <header className="header">
      <div className="header__left">
        <h1 className="header__title">{title}</h1>
        {subtitle && <p className="header__subtitle">{subtitle}</p>}
      </div>
      <div className="header__right">
        <StatusBadge status={status} label={label} />
      </div>
    </header>
  );
}
