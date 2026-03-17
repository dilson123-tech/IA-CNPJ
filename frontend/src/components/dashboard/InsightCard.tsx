type InsightCardProps = {
  title: string;
  text: string;
};

export default function InsightCard({ title, text }: InsightCardProps) {
  return (
    <article className="dashboard-card insight-card">
      <div className="dashboard-card-header">
        <h2>{title}</h2>
      </div>
      <p>{text}</p>
    </article>
  );
}
