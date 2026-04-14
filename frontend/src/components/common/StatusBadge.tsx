import './StatusBadge.css';

interface StatusBadgeProps {
  status: 'success' | 'warning' | 'error' | 'info' | 'neutral';
  label: string;
  size?: 'sm' | 'md';
}

export default function StatusBadge({
  status,
  label,
  size = 'md',
}: StatusBadgeProps) {
  return (
    <span className={`status-badge status-badge--${status} status-badge--${size}`}>
      <span className="status-badge__dot" />
      {label}
    </span>
  );
}
