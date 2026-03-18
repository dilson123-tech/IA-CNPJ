type StatusBannerProps = {
  message: string;
  variant?: 'error' | 'success' | 'info';
  actionLabel?: string;
  onAction?: () => void;
};

export default function StatusBanner({
  message,
  variant = 'info',
  actionLabel,
  onAction,
}: StatusBannerProps) {
  return (
    <div className={`status-banner status-banner-${variant}`}>
      <span>{message}</span>

      {actionLabel && onAction ? (
        <button
          type="button"
          className="status-banner-action"
          onClick={onAction}
        >
          {actionLabel}
        </button>
      ) : null}
    </div>
  );
}
