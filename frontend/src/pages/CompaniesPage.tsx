import { useEffect, useState } from 'react';
import AppShell from '../components/layout/AppShell';
import StatusBanner from '../components/layout/StatusBanner';
import ContentState from '../components/layout/ContentState';
import { createCompany, getCompanies, type Company } from '../services/api';

function normalizeCnpj(value: string): string {
  return value.replace(/\D/g, '').slice(0, 14);
}

function formatCnpj(value: string): string {
  const digits = normalizeCnpj(value);

  if (digits.length !== 14) {
    return value || 'Não informado';
  }

  return digits.replace(/^(\d{2})(\d{3})(\d{3})(\d{4})(\d{2})$/, '$1.$2.$3/$4-$5');
}

export default function CompaniesPage() {
  const [companies, setCompanies] = useState<Company[]>([]);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [cnpj, setCnpj] = useState('');
  const [razaoSocial, setRazaoSocial] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

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

  useEffect(() => {
    loadCompanies();
  }, []);

  async function handleCreateCompany(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setSuccess(null);

    const payload = {
      cnpj: normalizeCnpj(cnpj),
      razao_social: razaoSocial.trim(),
    };

    if (payload.cnpj.length !== 14) {
      setError('Informe um CNPJ com 14 dígitos.');
      return;
    }

    if (!payload.razao_social) {
      setError('Informe a razão social da empresa.');
      return;
    }

    try {
      setSubmitting(true);
      const created = await createCompany(payload);

      setCompanies((current) => [...current, created].sort((a, b) => a.id - b.id));
      setCnpj('');
      setRazaoSocial('');
      setShowCreateForm(false);
      setSuccess(`Empresa ${created.razao_social} cadastrada com sucesso.`);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Erro ao cadastrar empresa';
      setError(message);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <AppShell title="Empresas">
      {error ? <StatusBanner message={error} variant="error" /> : null}

      {success ? <StatusBanner message={success} variant="success" /> : null}

      <section className="page-card toolbar-card" style={{ marginBottom: '16px' }}>
        <div className="toolbar-card__top">
          <div>
            <h2 style={{ marginTop: 0, marginBottom: '8px' }}>Empresas cadastradas</h2>
            <p style={{ margin: 0, color: '#9aa4b2', lineHeight: 1.6 }}>
              Cadastre novas empresas e mantenha a base pronta para análises, relatórios
              e leitura consultiva.
            </p>
          </div>

          <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
            <span className="status-chip">
              {loading ? 'Carregando...' : `${companies.length} empresa(s)`}
            </span>

            <button
              className="control-button"
              type="button"
              onClick={() => {
                setShowCreateForm((current) => !current);
                setError(null);
                setSuccess(null);
              }}
            >
              {showCreateForm ? 'Fechar cadastro' : 'Nova empresa'}
            </button>
          </div>
        </div>

        {showCreateForm ? (
          <form onSubmit={handleCreateCompany} className="control-grid">
            <label className="control-field">
              <span>CNPJ</span>
              <input
                type="text"
                inputMode="numeric"
                placeholder="Somente números"
                value={cnpj}
                onChange={(event) => setCnpj(normalizeCnpj(event.target.value))}
              />
            </label>

            <label className="control-field">
              <span>Razão social</span>
              <input
                type="text"
                placeholder="Nome empresarial"
                value={razaoSocial}
                onChange={(event) => setRazaoSocial(event.target.value)}
              />
            </label>

            <div className="control-actions">
              <button className="control-button" type="submit" disabled={submitting}>
                {submitting ? 'Cadastrando...' : 'Salvar empresa'}
              </button>
            </div>

            <div className="control-actions">
              <button
                type="button"
                onClick={() => {
                  setShowCreateForm(false);
                  setCnpj('');
                  setRazaoSocial('');
                  setError(null);
                }}
                style={{
                  minHeight: '46px',
                  padding: '0 18px',
                  borderRadius: '14px',
                  fontWeight: 800,
                  cursor: 'pointer',
                  color: '#e2e8f0',
                  border: '1px solid rgba(148, 163, 184, 0.22)',
                  background: 'rgba(255,255,255,0.03)',
                }}
              >
                Cancelar
              </button>
            </div>
          </form>
        ) : null}
      </section>

      <div className="page-card">
        {loading ? (
          <ContentState message="Carregando empresas..." tone="loading" />
        ) : companies.length === 0 ? (
          <ContentState message="Nenhuma empresa encontrada. Cadastre a primeira para começar." tone="empty" />
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
                <strong style={{ display: 'block', marginBottom: '6px' }}>
                  {company.razao_social}
                </strong>
                <span style={{ display: 'block', color: '#9aa4b2' }}>
                  CNPJ: {formatCnpj(company.cnpj)}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>
    </AppShell>
  );
}
