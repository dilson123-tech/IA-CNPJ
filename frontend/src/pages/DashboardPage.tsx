import { useEffect, useMemo, useState } from 'react';
import AppShell from '../components/layout/AppShell';
import StatusBanner from '../components/layout/StatusBanner';
import SummaryCard from '../components/dashboard/SummaryCard';
import RecentTransactionsCard from '../components/dashboard/RecentTransactionsCard';
import QuickActionsCard from '../components/dashboard/QuickActionsCard';
import InsightCard from '../components/dashboard/InsightCard';
import KpiListCard from '../components/dashboard/KpiListCard';
import { getCompanies, getTransactions, type Company, type Transaction } from '../services/api';

function formatCurrencyFromCents(value: number): string {
  return new Intl.NumberFormat('pt-BR', {
    style: 'currency',
    currency: 'BRL',
  }).format(value / 100);
}

function formatDate(value: string): string {
  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return new Intl.DateTimeFormat('pt-BR', {
    dateStyle: 'short',
    timeStyle: 'short',
  }).format(date);
}

export default function DashboardPage() {
  const [companies, setCompanies] = useState<Company[]>([]);
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  async function loadDashboard() {
    try {
      setLoading(true);
      setError(null);

      const [companiesData, transactionsData] = await Promise.all([
        getCompanies(),
        getTransactions(),
      ]);

      setCompanies(companiesData);
      setTransactions(transactionsData);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Erro ao carregar dashboard';
      setError(message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadDashboard();
  }, []);

  const visibleCompanyIds = useMemo(
    () => new Set(companies.map((company) => company.id)),
    [companies]
  );

  const visibleTransactions = useMemo(
    () =>
      transactions.filter((transaction) => visibleCompanyIds.has(transaction.company_id)),
    [transactions, visibleCompanyIds]
  );

  const metrics = useMemo(() => {
    const totalIn = visibleTransactions
      .filter((transaction) => transaction.kind === 'in')
      .reduce((sum, transaction) => sum + transaction.amount_cents, 0);

    const totalOut = visibleTransactions
      .filter((transaction) => transaction.kind === 'out')
      .reduce((sum, transaction) => sum + transaction.amount_cents, 0);

    const totalProcessed = visibleTransactions.reduce(
      (sum, transaction) => sum + transaction.amount_cents,
      0
    );

    const monthlyResult = totalIn - totalOut;

    const recentItems = [...visibleTransactions]
      .sort(
        (a, b) =>
          new Date(b.occurred_at).getTime() - new Date(a.occurred_at).getTime()
      )
      .slice(0, 5)
      .map((transaction) => ({
        id: String(transaction.id),
        title: transaction.description || `Transação #${transaction.id}`,
        subtitle: `${transaction.kind === 'in' ? 'Entrada' : 'Saída'} • ${formatDate(
          transaction.occurred_at
        )}`,
        amount: `${transaction.kind === 'in' ? '+' : '-'} ${formatCurrencyFromCents(
          transaction.amount_cents
        )}`,
      }));

    return {
      totalIn,
      totalOut,
      totalProcessed,
      monthlyResult,
      recentItems,
    };
  }, [visibleTransactions]);

  return (
    <AppShell title="Dashboard">
      {error ? (
        <StatusBanner
          message={error}
          variant="error"
          actionLabel="Tentar novamente"
          onAction={() => {
            void loadDashboard();
          }}
        />
      ) : null}

      <section className="dashboard-grid dashboard-grid-summary">
        <SummaryCard
          title="Empresas monitoradas"
          value={loading ? '...' : String(companies.length)}
          subtitle="Total de empresas cadastradas"
        />
        <SummaryCard
          title="Transações processadas"
          value={loading ? '...' : String(visibleTransactions.length)}
          subtitle="Quantidade total registrada"
        />
        <SummaryCard
          title="Volume processado"
          value={loading ? '...' : formatCurrencyFromCents(metrics.totalProcessed)}
          subtitle="Entradas + saídas registradas"
        />
        <SummaryCard
          title="Resultado do mês"
          value={loading ? '...' : formatCurrencyFromCents(metrics.monthlyResult)}
          subtitle="Entradas menos saídas"
        />
      </section>

      <section className="dashboard-grid dashboard-grid-main">
        <RecentTransactionsCard
          items={
            loading
              ? [
                  {
                    id: 'loading',
                    title: 'Carregando transações...',
                    subtitle: 'Aguarde',
                    amount: '...',
                  },
                ]
              : metrics.recentItems.length > 0
              ? metrics.recentItems
              : [
                  {
                    id: 'empty',
                    title: 'Nenhuma transação encontrada',
                    subtitle: 'Cadastre movimentações para alimentar o painel',
                    amount: '--',
                  },
                ]
          }
        />

        <QuickActionsCard
          actions={[
            { label: 'Ver empresas', to: '/companies' },
            { label: 'Abrir relatórios', to: '/reports' },
            { label: 'Consultar IA', to: '/ai-consult' },
          ]}
        />

        <KpiListCard
          title="KPIs rápidos"
          items={[
            {
              label: 'Empresas cadastradas',
              value: loading ? '...' : String(companies.length),
            },
            {
              label: 'Entradas',
              value: loading ? '...' : formatCurrencyFromCents(metrics.totalIn),
            },
            {
              label: 'Saídas',
              value: loading ? '...' : formatCurrencyFromCents(metrics.totalOut),
            },
            {
              label: 'Últimos lançamentos',
              value: loading ? '...' : String(metrics.recentItems.length),
            },
          ]}
        />

        <InsightCard
          title="Insight consultivo"
          text={
            loading
              ? 'Carregando leitura operacional do ambiente...'
              : visibleTransactions.length > 0
              ? `A vitrine oficial já possui ${visibleTransactions.length} transação(ões) visíveis, com volume total de ${formatCurrencyFromCents(
                  metrics.totalProcessed
                )} e resultado atual de ${formatCurrencyFromCents(
                  metrics.monthlyResult
                )}. Próximo passo estratégico: ligar relatórios e IA consultiva para transformar essa leitura em recomendação executiva.`
              : 'Nenhuma transação visível no painel oficial. O próximo passo é cadastrar dados reais para alimentar a vitrine executiva.'
          }
        />
      </section>
    </AppShell>
  );
}
