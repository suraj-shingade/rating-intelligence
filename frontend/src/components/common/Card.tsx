import type { ReactNode } from 'react';
import './Card.css';

interface CardProps {
  title?: string;
  subtitle?: string;
  children: ReactNode;
  className?: string;
  headerAction?: ReactNode;
  noPadding?: boolean;
}

export default function Card({
  title,
  subtitle,
  children,
  className = '',
  headerAction,
  noPadding = false,
}: CardProps) {
  return (
    <div className={`card ${className}`}>
      {(title || headerAction) && (
        <div className="card__header">
          <div className="card__header-text">
            {title && <h3 className="card__title">{title}</h3>}
            {subtitle && <p className="card__subtitle">{subtitle}</p>}
          </div>
          {headerAction && (
            <div className="card__header-action">{headerAction}</div>
          )}
        </div>
      )}
      <div className={`card__body ${noPadding ? 'card__body--no-padding' : ''}`}>
        {children}
      </div>
    </div>
  );
}
