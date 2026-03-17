import { Link } from 'react-router-dom';

type QuickAction = {
  label: string;
  to: string;
};

type QuickActionsCardProps = {
  actions: QuickAction[];
};

export default function QuickActionsCard({ actions }: QuickActionsCardProps) {
  return (
    <article className="dashboard-card">
      <div className="dashboard-card-header">
        <h2>Ações rápidas</h2>
      </div>

      <div className="quick-actions">
        {actions.map((action) => (
          <Link key={action.to} to={action.to} className="quick-action-button">
            {action.label}
          </Link>
        ))}
      </div>
    </article>
  );
}
