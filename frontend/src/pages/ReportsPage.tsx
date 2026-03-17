import { useEffect, useState } from 'react';
import AppShell from '../components/layout/AppShell';
import {
  getCompanies,
  getReportContext,
  getReportSummary,
  type Company,
  type ReportContextResponse,
  type ReportSummaryResponse,
} from '../services/api';

function formatCurrencyFromCents(value: number): string {
  return new Intl.NumberFormat('pt-BR', {
    style: 'currency',
    currency: 'BRL',
  }).format(value / 100);
}

function formatDateTime(value: string): string {
  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return new Intl.DateTimeFormat('pt-BR', {
    dateStyle: 'short',
    timeStyle: 'short',
  }).format(date);
}

export default function ReportsPage() {
  const [company, setCompany] = useState<Company | null>(null);
  const [summary, setSummary] = useState<ReportSummaryResponse | null>(null);
  const [context, setContext] = useState<ReportContextResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadReports() {
      try {
        setLoading(true);
        setError(null);

        const companies = await getCompanies();
        const firstCompany = companies[0] || null;

        setCompany(firstCompany);

        if (!firstCompany) {
          setSummary(null);
          setContext(null);
          return;
        }

        const [summaryData, contextData] = await Promise.all([
          getReportSummary({ company_id: firstCompany.id }),
          getReportContext({ company_id: firstCompany.id, limit: 10 }),
        ]);

        setSummary(summaryData);
        setContext(contextData);
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Erro ao carregar relatórios';
        setError(message);
      } finally {
        setLoading(false);
      }
    }

    loadReports();
  }, []);

  return (
    <AppShell title="Relatórios">
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
        <h2 style={{ marginTop: 0, marginBottom: '8px' }}>Resumo executivo</h2>
        <p style={{ margin: 0, color: '#9aa4b2', lineHeight: 1.6 }}>
          {loading
            ? 'Carregando relatório executivo...'
            : company
            ? `Empresa-base da leitura: ${company.razao_social}${company.cnpj ? ` • ${company.cnpj}` : ''}`
            : 'Nenhuma empresa disponível para gerar relatório.'}
        </p>
      </section>

      <section
        className="dashboard-grid dashboard-grid-summary"
        style={{ marginBottom: '16px' }}
      >
        <article className="summary-card">
          <p className="summary-card-title">Entradas</p>
          <strong className="summary-card-value">
            {loading || !summary ? '...' : formatCurrencyFromCents(summary.totals.entradas_cents)}
          </strong>
          <span className="summary-card-subtitle">Total de entradas no período</span>
        </article>

        <article className="summary-card">
          <p className="summary-card-title">Saídas</p>
          <strong className="summary-card-value">
            {loading || !summary ? '...' : formatCurrencyFromCents(summary.totals.saidas_cents)}
          </strong>
          <span className="summary-card-subtitle">Total de saídas no período</span>
        </article>

        <article className="summary-card">
          <p className="summary-card-title">Saldo</p>
          <strong className="summary-card-value">
            {loading || !summary ? '...' : formatCurrencyFromCents(summary.totals.saldo_cents)}
          </strong>
          <span className="summary-card-subtitle">Resultado consolidado</span>
        </article>

        <article className="summary-card">
          <p className="summary-card-title">Categorias</p>
          <strong className="summary-card-value">
            {loading || !summary ? '...' : String(summary.by_category.length)}
          </strong>
          <span className="summary-card-subtitle">Categorias encontradas no período</span>
        </article>
      </section>

      <section className="dashboard-grid dashboard-grid-main">
        <article className="dashboard-card">
          <div className="dashboard-card-header">
            <h2>Quebra por categoria</h2>
          </div>

          {loading ? (
            <p>Carregando categorias...</p>
          ) : !summary || summary.by_category.length === 0 ? (
            <p>Nenhuma categoria encontrada.</p>
          ) : (
            <div className="kpi-list">
              {summary.by_category.map((item) => (
                <div key={`${item.category_id ?? 'sem'}-${item.category_name}`} className="kpi-list-item">
                  <span>{item.category_name}</span>
                  <strong>{formatCurrencyFromCents(item.saldo_cents)}</strong>
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
          ) : !context || context.recent_transactions.length === 0 ? (
            <p>Nenhuma transação encontrada no contexto.</p>
          ) : (
            <div className="dashboard-list">
              {context.recent_transactions.map((item) => (
                <div key={item.id} className="dashboard-list-item">
                  <div>
                    <strong>{item.description || `Transação #${item.id}`}</strong>
                    <p>
                      {item.category_name} • {formatDateTime(item.occurred_at)}
                    </p>
                  </div>
                  <span>
                    {item.kind === 'in' ? '+' : '-'} {formatCurrencyFromCents(item.amount_cents)}
                  </span>
                </div>
              ))}
            </div>
          )}
        </article>

        <article className="dashboard-card">
          <div className="dashboard-card-header">
            <h2>Contexto executivo</h2>
          </div>

          <p style={{ color: '#9aa4b2', lineHeight: 1.7 }}>
            {loading
              ? 'Montando leitura contextual do período...'
              : summary
              ? `O relatório real da empresa selecionada aponta entradas de ${formatCurrencyFromCents(
                  summary.totals.entradas_cents
                )}, saídas de ${formatCurrencyFromCents(
                  summary.totals.saidas_cents
                )} e saldo consolidado de ${formatCurrencyFromCents(
                  summary.totals.saldo_cents
                )}. Esse bloco já está consumindo os endpoints reais de summary e context do engine IA-CNPJ.`
              : 'Sem dados suficientes para leitura executiva no momento.'}
          </p>
        </article>
      </section>
    </AppShell>
  );
}
