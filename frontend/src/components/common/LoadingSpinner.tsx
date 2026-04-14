import './LoadingSpinner.css';

interface LoadingSpinnerProps {
  size?: 'sm' | 'md' | 'lg';
  message?: string;
}

export default function LoadingSpinner({
  size = 'md',
  message,
}: LoadingSpinnerProps) {
  return (
    <div className="loading-spinner-container">
      <div className={`loading-spinner loading-spinner--${size}`}>
        <div className="loading-spinner__ring" />
      </div>
      {message && <p className="loading-spinner__message">{message}</p>}
    </div>
  );
}
