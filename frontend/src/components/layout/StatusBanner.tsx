type StatusBannerProps = {
  message: string;
  variant?: 'error' | 'success' | 'info';
};

export default function StatusBanner({
  message,
  variant = 'info',
}: StatusBannerProps) {
  return <div className={`status-banner status-banner-${variant}`}>{message}</div>;
}
