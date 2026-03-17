type SummaryCardProps = {
  title: string;
  value: string;
  subtitle: string;
};

export default function SummaryCard({ title, value, subtitle }: SummaryCardProps) {
  return (
    <article className="summary-card">
      <p className="summary-card-title">{title}</p>
      <strong className="summary-card-value">{value}</strong>
      <span className="summary-card-subtitle">{subtitle}</span>
    </article>
  );
}
