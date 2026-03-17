import { useEffect, useState } from 'react';
import AppShell from '../components/layout/AppShell';
import { getCompanies, type Company } from '../services/api';

export default function CompaniesPage() {
  const [companies, setCompanies] = useState<Company[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadCompanies() {
      try {
        setLoading(true);
        setError(null);
        const data = await getCompanies();
        setCompanies(data);
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Erro ao carregar empresas';
        setError(message);
      } finally {
        setLoading(false);
      }
    }

    loadCompanies();
  }, []);

  return (
    <AppShell title="Empresas">
      {error ? (
        <div style={{ marginBottom: '16px', padding: '12px 16px', borderRadius: '12px', background: '#3a1620', color: '#ffd5db' }}>
          {error}
        </div>
      ) : null}

      <div className="page-card">
        <h2 style={{ marginTop: 0 }}>Empresas cadastradas</h2>

        {loading ? (
          <p>Carregando empresas...</p>
        ) : companies.length === 0 ? (
          <p>Nenhuma empresa encontrada.</p>
        ) : (
          <div style={{ display: 'grid', gap: '12px' }}>
            {companies.map((company) => (
              <div
                key={company.id}
                style={{
                  padding: '16px',
                  border: '1px solid rgba(255,255,255,0.08)',
                  borderRadius: '14px',
                  background: 'rgba(255,255,255,0.02)',
                }}
              >
                <strong style={{ display: 'block', marginBottom: '6px' }}>{company.razao_social}</strong>
                <span style={{ display: 'block', color: '#9aa4b2' }}>
                  CNPJ: {company.cnpj || 'Não informado'}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>
    </AppShell>
  );
}
