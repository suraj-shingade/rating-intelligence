import './DisclaimerBanner.css';

interface DisclaimerBannerProps {
  text: string;
}

export default function DisclaimerBanner({ text }: DisclaimerBannerProps) {
  return (
    <div className="disclaimer-banner">
      <div className="disclaimer-banner__icon">i</div>
      <p className="disclaimer-banner__text">{text}</p>
    </div>
  );
}
