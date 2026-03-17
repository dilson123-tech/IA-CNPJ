type KpiItem = {
  label: string;
  value: string;
};

type KpiListCardProps = {
  title: string;
  items: KpiItem[];
};

export default function KpiListCard({ title, items }: KpiListCardProps) {
  return (
    <article className="dashboard-card">
      <div className="dashboard-card-header">
        <h2>{title}</h2>
      </div>

      <div className="kpi-list">
        {items.map((item) => (
          <div key={item.label} className="kpi-list-item">
            <span>{item.label}</span>
            <strong>{item.value}</strong>
          </div>
        ))}
      </div>
    </article>
  );
}
