import { useEffect, useState } from 'react';
import AppShell from '../components/layout/AppShell';
import {
  getAIConsult,
  getCompanies,
  type AIConsultResponse,
  type Company,
} from '../services/api';

const DEMO_PERIOD = {
  start: '2026-01-01',
  end: '2026-12-31',
};

function formatCurrencyFromCents(value: number): string {
  return new Intl.NumberFormat('pt-BR', {
    style: 'currency',
    currency: 'BRL',
  }).format(value / 100);
}

function formatDateTime(value?: string | null): string {
  if (!value) {
    return 'Data indisponível';
  }

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return new Intl.DateTimeFormat('pt-BR', {
    dateStyle: 'short',
    timeStyle: 'short',
  }).format(date);
}

export default function AIConsultPage() {
  const [company, setCompany] = useState<Company | null>(null);
  const [consult, setConsult] = useState<AIConsultResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadAIConsult() {
      try {
        setLoading(true);
        setError(null);

        const companies = await getCompanies();
        const firstCompany = companies[0] || null;

        setCompany(firstCompany);

        if (!firstCompany) {
          setConsult(null);
          return;
        }

        const consultData = await getAIConsult({
          company_id: firstCompany.id,
          start: DEMO_PERIOD.start,
          end: DEMO_PERIOD.end,
          limit: 10,
        });

        setConsult(consultData);
      } catch (err) {
        const message =
          err instanceof Error ? err.message : 'Erro ao carregar análise consultiva';
        setError(message);
      } finally {
        setLoading(false);
      }
    }

    loadAIConsult();
  }, []);

  return (
    <AppShell title="IA Consultiva">
      {error ? (
        <div
          style={{
            marginBottom: '16px',
            padding: '12px 16px',
            borderRadius: '12px',
            background: '#3a1620',
            color: '#ffd5db',
          }}
        >
          {error}
        </div>
      ) : null}

      <section className="page-card" style={{ marginBottom: '16px' }}>
        <h2 style={{ marginTop: 0, marginBottom: '8px' }}>Leitura consultiva real</h2>
        <p style={{ margin: 0, color: '#9aa4b2', lineHeight: 1.6 }}>
          {loading
            ? 'Carregando análise consultiva...'
            : company
            ? `Empresa-base da leitura: ${company.razao_social}${
                company.cnpj ? ` • ${company.cnpj}` : ''
              } • Período ${DEMO_PERIOD.start} até ${DEMO_PERIOD.end}`
            : 'Nenhuma empresa disponível para consultar a IA.'}
        </p>
      </section>

      <section
        className="dashboard-grid dashboard-grid-summary"
        style={{ marginBottom: '16px' }}
      >
        <article className="summary-card">
          <p className="summary-card-title">Entradas</p>
          <strong className="summary-card-value">
            {loading || !consult ? '...' : formatCurrencyFromCents(consult.numbers.entradas_cents)}
          </strong>
          <span className="summary-card-subtitle">Total de entradas analisadas</span>
        </article>

        <article className="summary-card">
          <p className="summary-card-title">Saídas</p>
          <strong className="summary-card-value">
            {loading || !consult ? '...' : formatCurrencyFromCents(consult.numbers.saidas_cents)}
          </strong>
          <span className="summary-card-subtitle">Total de saídas analisadas</span>
        </article>

        <article className="summary-card">
          <p className="summary-card-title">Saldo</p>
          <strong className="summary-card-value">
            {loading || !consult ? '...' : formatCurrencyFromCents(consult.numbers.saldo_cents)}
          </strong>
          <span className="summary-card-subtitle">Resultado consolidado da IA</span>
        </article>

        <article className="summary-card">
          <p className="summary-card-title">Transações</p>
          <strong className="summary-card-value">
            {loading || !consult ? '...' : String(consult.numbers.qtd_transacoes)}
          </strong>
          <span className="summary-card-subtitle">Itens considerados na leitura</span>
        </article>
      </section>

      <section className="dashboard-grid dashboard-grid-main">
        <article className="dashboard-card">
          <div className="dashboard-card-header">
            <h2>Headline da IA</h2>
          </div>

          <p style={{ color: '#9aa4b2', lineHeight: 1.7, marginBottom: '12px' }}>
            {loading
              ? 'Gerando headline executiva...'
              : consult?.headline || 'Sem headline disponível no momento.'}
          </p>

          <p style={{ color: '#7f8b99', margin: 0, fontSize: '14px' }}>
            {loading || !consult
              ? '...'
              : `Gerado em ${formatDateTime(consult.generated_at)}`}
          </p>
        </article>

        <article className="dashboard-card">
          <div className="dashboard-card-header">
            <h2>Insights</h2>
          </div>

          {loading ? (
            <p>Carregando insights...</p>
          ) : !consult || consult.insights.length === 0 ? (
            <p>Nenhum insight retornado.</p>
          ) : (
            <div className="kpi-list">
              {consult.insights.map((item, index) => (
                <div key={`insight-${index}`} className="kpi-list-item">
                  <span>{item}</span>
                </div>
              ))}
            </div>
          )}
        </article>

        <article className="dashboard-card">
          <div className="dashboard-card-header">
            <h2>Riscos</h2>
          </div>

          {loading ? (
            <p>Carregando riscos...</p>
          ) : !consult || consult.risks.length === 0 ? (
            <p>Nenhum risco crítico retornado.</p>
          ) : (
            <div className="kpi-list">
              {consult.risks.map((item, index) => (
                <div key={`risk-${index}`} className="kpi-list-item">
                  <span>{item}</span>
                </div>
              ))}
            </div>
          )}
        </article>

        <article className="dashboard-card">
          <div className="dashboard-card-header">
            <h2>Ações recomendadas</h2>
          </div>

          {loading ? (
            <p>Carregando ações...</p>
          ) : !consult || consult.actions.length === 0 ? (
            <p>Nenhuma ação recomendada no momento.</p>
          ) : (
            <div className="kpi-list">
              {consult.actions.map((item, index) => (
                <div key={`action-${index}`} className="kpi-list-item">
                  <span>{item}</span>
                </div>
              ))}
            </div>
          )}
        </article>

        <article className="dashboard-card">
          <div className="dashboard-card-header">
            <h2>Top categorias</h2>
          </div>

          {loading ? (
            <p>Carregando categorias...</p>
          ) : !consult || consult.top_categories.length === 0 ? (
            <p>Nenhuma categoria retornada.</p>
          ) : (
            <div className="dashboard-list">
              {consult.top_categories.map((item) => (
                <div
                  key={`${item.category_id ?? 'sem'}-${item.category_name}`}
                  className="dashboard-list-item"
                >
                  <div>
                    <strong>{item.category_name}</strong>
                    <p>{item.qtd_transacoes} transação(ões) no período</p>
                  </div>
                  <span>{formatCurrencyFromCents(item.saldo_cents)}</span>
                </div>
              ))}
            </div>
          )}
        </article>

        <article className="dashboard-card">
          <div className="dashboard-card-header">
            <h2>Transações recentes</h2>
          </div>

          {loading ? (
            <p>Carregando transações...</p>
          ) : !consult || consult.recent_transactions.length === 0 ? (
            <p>Nenhuma transação recente retornada.</p>
          ) : (
            <div className="dashboard-list">
              {consult.recent_transactions.map((item) => (
                <div key={item.id} className="dashboard-list-item">
                  <div>
                    <strong>{item.description || `Transação #${item.id}`}</strong>
                    <p>
                      {item.category_name} • {formatDateTime(item.occurred_at)}
                    </p>
                  </div>
                  <span>
                    {item.kind === 'in' ? '+' : '-'}{' '}
                    {formatCurrencyFromCents(item.amount_cents)}
                  </span>
                </div>
              ))}
            </div>
          )}
        </article>
      </section>
    </AppShell>
  );
}
