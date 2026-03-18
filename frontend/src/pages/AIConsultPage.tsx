import { useEffect, useMemo, useState } from 'react';
import AppShell from '../components/layout/AppShell';
import StatusBanner from '../components/layout/StatusBanner';
import ContentState from '../components/layout/ContentState';
import {
  getAIConsult,
  getCompanies,
  type AIConsultResponse,
  type Company,
} from '../services/api';

const DEFAULT_PERIOD = {
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
  const [companies, setCompanies] = useState<Company[]>([]);
  const [selectedCompanyId, setSelectedCompanyId] = useState('');
  const [startDate, setStartDate] = useState(DEFAULT_PERIOD.start);
  const [endDate, setEndDate] = useState(DEFAULT_PERIOD.end);
  const [consult, setConsult] = useState<AIConsultResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const selectedCompany = useMemo(
    () => companies.find((company) => String(company.id) === selectedCompanyId) || null,
    [companies, selectedCompanyId]
  );

  async function loadConsult(params: {
    companyId: number;
    start: string;
    end: string;
  }) {
    try {
      setLoading(true);
      setError(null);

      const consultData = await getAIConsult({
        company_id: params.companyId,
        start: params.start,
        end: params.end,
        limit: 10,
      });

      setConsult(consultData);
    } catch (err) {
      const message =
        err instanceof Error ? err.message : 'Erro ao carregar análise consultiva';
      setError(message);
      setConsult(null);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    async function bootstrap() {
      try {
        setLoading(true);
        setError(null);

        const companiesData = await getCompanies();
        setCompanies(companiesData);

        const firstCompany = companiesData[0] || null;

        if (!firstCompany) {
          setSelectedCompanyId('');
          setConsult(null);
          return;
        }

        setSelectedCompanyId(String(firstCompany.id));

        const consultData = await getAIConsult({
          company_id: firstCompany.id,
          start: DEFAULT_PERIOD.start,
          end: DEFAULT_PERIOD.end,
          limit: 10,
        });

        setConsult(consultData);
      } catch (err) {
        const message =
          err instanceof Error ? err.message : 'Erro ao carregar análise consultiva';
        setError(message);
        setConsult(null);
      } finally {
        setLoading(false);
      }
    }

    bootstrap();
  }, []);

  async function handleRefresh() {
    if (!selectedCompanyId) {
      setError('Selecione uma empresa para atualizar a análise.');
      return;
    }

    await loadConsult({
      companyId: Number(selectedCompanyId),
      start: startDate,
      end: endDate,
    });
  }

  function handleClearFilters() {
    setSelectedCompanyId('');
    setStartDate(DEFAULT_PERIOD.start);
    setEndDate(DEFAULT_PERIOD.end);
    setConsult(null);
    setError(null);
    setLoading(false);
  }

  return (
    <AppShell title="IA Consultiva">
      {error ? <StatusBanner message={error} variant="error" /> : null}

      <section className="page-card toolbar-card" style={{ marginBottom: '16px' }}>
        <div className="toolbar-card__top">
          <div>
            <h2 style={{ marginTop: 0, marginBottom: '8px' }}>Leitura consultiva</h2>
            <p style={{ margin: 0, color: '#9aa4b2', lineHeight: 1.6 }}>
              Analise uma empresa, ajuste o período e gere uma leitura executiva com
              headline, riscos, ações e transações recentes.
            </p>
          </div>

          <span className="status-chip">
            {loading
              ? 'Atualizando análise...'
              : consult
              ? 'Dados reais ativos'
              : 'Pronto para nova análise'}
          </span>
        </div>

        <div className="control-grid">
          <label className="control-field">
            <span>Empresa</span>
            <select
              value={selectedCompanyId}
              onChange={(event) => setSelectedCompanyId(event.target.value)}
              disabled={loading && companies.length === 0}
            >
              <option value="">Selecione uma empresa</option>
              {companies.map((company) => (
                <option key={company.id} value={company.id}>
                  {company.razao_social}
                </option>
              ))}
            </select>
          </label>

          <label className="control-field">
            <span>Data inicial</span>
            <input
              type="date"
              value={startDate}
              onChange={(event) => setStartDate(event.target.value)}
            />
          </label>

          <label className="control-field">
            <span>Data final</span>
            <input
              type="date"
              value={endDate}
              onChange={(event) => setEndDate(event.target.value)}
            />
          </label>

          <div className="control-actions">
            <button
              className="control-button"
              type="button"
              onClick={handleRefresh}
              disabled={loading || !selectedCompanyId}
            >
              {loading ? 'Atualizando...' : 'Atualizar análise'}
            </button>

            <button
              className="control-button"
              type="button"
              onClick={handleClearFilters}
              disabled={loading}
              style={{
                background: 'transparent',
                color: '#e7ecf3',
                border: '1px solid rgba(231, 236, 243, 0.18)',
                boxShadow: 'none',
              }}
            >
              Limpar filtros
            </button>
          </div>
        </div>

        <p style={{ margin: 0, color: '#9aa4b2', lineHeight: 1.6 }}>
          {loading
            ? 'Carregando análise consultiva...'
            : selectedCompany
            ? `Empresa selecionada: ${selectedCompany.razao_social}${
                selectedCompany.cnpj ? ` • ${selectedCompany.cnpj}` : ''
              } • Período ${startDate} até ${endDate}`
            : companies.length === 0
            ? 'Nenhuma empresa disponível para consultar a IA.'
            : 'Selecione uma empresa e defina o período para gerar uma nova análise.'}
        </p>
      </section>

      <section
        className="dashboard-grid dashboard-grid-summary"
        style={{ marginBottom: '16px' }}
      >
        <article className="summary-card">
          <p className="summary-card-title">Entradas</p>
          <strong className="summary-card-value">
            {loading ? '...' : consult ? formatCurrencyFromCents(consult.numbers.entradas_cents) : '—'}
          </strong>
          <span className="summary-card-subtitle">Total de entradas analisadas</span>
        </article>

        <article className="summary-card">
          <p className="summary-card-title">Saídas</p>
          <strong className="summary-card-value">
            {loading ? '...' : consult ? formatCurrencyFromCents(consult.numbers.saidas_cents) : '—'}
          </strong>
          <span className="summary-card-subtitle">Total de saídas analisadas</span>
        </article>

        <article className="summary-card">
          <p className="summary-card-title">Saldo</p>
          <strong className="summary-card-value">
            {loading ? '...' : consult ? formatCurrencyFromCents(consult.numbers.saldo_cents) : '—'}
          </strong>
          <span className="summary-card-subtitle">Resultado consolidado da IA</span>
        </article>

        <article className="summary-card">
          <p className="summary-card-title">Transações</p>
          <strong className="summary-card-value">
            {loading ? '...' : consult ? String(consult.numbers.qtd_transacoes) : '—'}
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
            {loading
              ? '...'
              : consult
              ? `Gerado em ${formatDateTime(consult.generated_at)}`
              : 'Defina os filtros e gere uma nova análise.'}
          </p>
        </article>

        <article className="dashboard-card">
          <div className="dashboard-card-header">
            <h2>Insights</h2>
          </div>

          {loading ? (
            <ContentState message="Carregando insights..." tone="loading" />
          ) : !consult || consult.insights.length === 0 ? (
            <ContentState message="Nenhum insight retornado." tone="empty" />
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
            <ContentState message="Carregando riscos..." tone="loading" />
          ) : !consult || consult.risks.length === 0 ? (
            <ContentState message="Nenhum risco crítico retornado." tone="empty" />
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
            <ContentState message="Carregando ações..." tone="loading" />
          ) : !consult || consult.actions.length === 0 ? (
            <ContentState message="Nenhuma ação recomendada no momento." tone="empty" />
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
            <ContentState message="Carregando categorias..." tone="loading" />
          ) : !consult || consult.top_categories.length === 0 ? (
            <ContentState message="Nenhuma categoria retornada." tone="empty" />
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
            <ContentState message="Carregando transações..." tone="loading" />
          ) : !consult || consult.recent_transactions.length === 0 ? (
            <ContentState message="Nenhuma transação recente retornada." tone="empty" />
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
