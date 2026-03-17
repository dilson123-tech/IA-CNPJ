type RecentItem = {
  id: string;
  title: string;
  subtitle: string;
  amount: string;
};

type RecentTransactionsCardProps = {
  items: RecentItem[];
};

export default function RecentTransactionsCard({ items }: RecentTransactionsCardProps) {
  return (
    <article className="dashboard-card">
      <div className="dashboard-card-header">
        <h2>Empresas recentes</h2>
      </div>

      <div className="dashboard-list">
        {items.map((item) => (
          <div key={item.id} className="dashboard-list-item">
            <div>
              <strong>{item.title}</strong>
              <p>{item.subtitle}</p>
            </div>
            <span>{item.amount}</span>
          </div>
        ))}
      </div>
    </article>
  );
}
