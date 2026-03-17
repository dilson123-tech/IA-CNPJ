import AppShell from '../components/layout/AppShell';

export default function AIConsultPage() {
  return (
    <AppShell title="IA Consultiva">
      <section className="page-card">
        <div
          className="card insight-card insight-card-neutral"
          style={{
            padding: '24px',
            borderRadius: '18px',
            border: '1px solid rgba(255,255,255,0.08)',
            background: 'rgba(255,255,255,0.02)',
          }}
        >
          <span
            style={{
              display: 'inline-block',
              marginBottom: '12px',
              padding: '6px 10px',
              borderRadius: '999px',
              fontSize: '12px',
              border: '1px solid rgba(255,255,255,0.12)',
              color: '#9aa4b2',
            }}
          >
            Módulo em preparação
          </span>

          <h2
            className="section-heading__title"
            style={{ margin: '0 0 12px 0' }}
          >
            IA consultiva em integração
          </h2>

          <p
            className="insight-card__description"
            style={{ margin: 0, color: '#9aa4b2', lineHeight: 1.6 }}
          >
            Esta área será conectada ao motor real de análise consultiva da IA-CNPJ.
            O próximo passo é consumir o backend autenticado e exibir diagnósticos,
            insights financeiros e recomendações acionáveis por tenant.
          </p>
        </div>
      </section>
    </AppShell>
  );
}
