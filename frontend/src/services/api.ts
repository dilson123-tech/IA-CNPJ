import { clearToken, getToken } from './auth';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8110';

type RequestOptions = RequestInit & {
  auth?: boolean;
};

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { auth = false, headers, ...rest } = options;

  const finalHeaders = new Headers(headers || {});
  finalHeaders.set('Content-Type', 'application/json');

  if (auth) {
    const token = getToken();
    if (token) {
      finalHeaders.set('Authorization', `Bearer ${token}`);
    }
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...rest,
    headers: finalHeaders,
  });

  if (!response.ok) {
    let message = 'Erro ao processar a requisição';

    try {
      const errorData = await response.json();
      message = errorData.detail || errorData.message || message;
    } catch {
      // segue com mensagem padrão
    }

    if (response.status === 401) {
      clearToken();

      if (typeof window !== 'undefined' && window.location.pathname !== '/login') {
        window.location.href = '/login';
      }

      throw new Error('Sessão expirada. Faça login novamente.');
    }

    throw new Error(typeof message === 'string' ? message : 'Erro ao processar a requisição');
  }

  if (response.status === 204) {
    return null as T;
  }

  return response.json();
}

function buildQuery(params: Record<string, string | number | undefined | null>): string {
  const search = new URLSearchParams();

  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== null && value !== '') {
      search.set(key, String(value));
    }
  }

  const qs = search.toString();
  return qs ? `?${qs}` : '';
}

export type LoginPayload = {
  username: string;
  password: string;
};

export type LoginResponse = {
  access_token: string;
  token_type: string;
};

export type Company = {
  id: number;
  cnpj: string;
  razao_social: string;
};

export type Transaction = {
  id: number;
  company_id: number;
  kind: 'in' | 'out';
  amount_cents: number;
  description: string;
  occurred_at: string;
  category_id?: number | null;
};

export type ReportPeriod = {
  start: string;
  end: string;
};

export type ReportTotals = {
  entradas_cents: number;
  saidas_cents: number;
  saldo_cents: number;
};

export type ReportCategoryBreakdown = {
  category_id?: number | null;
  category_name: string;
  entradas_cents: number;
  saidas_cents: number;
  saldo_cents: number;
};

export type ReportSummaryResponse = {
  company_id: number;
  period: ReportPeriod;
  totals: ReportTotals;
  by_category: ReportCategoryBreakdown[];
};

export type ReportContextTransaction = {
  id: number;
  occurred_at: string;
  kind: 'in' | 'out';
  amount_cents: number;
  category_id?: number | null;
  category_name: string;
  description: string;
};

export type ReportContextResponse = {
  company_id: number;
  period: ReportPeriod;
  totals: ReportTotals;
  by_category: ReportCategoryBreakdown[];
  recent_transactions: ReportContextTransaction[];
};

export async function login(payload: LoginPayload): Promise<LoginResponse> {
  return request<LoginResponse>('/api/v1/auth/login', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export async function getCompanies(): Promise<Company[]> {
  return request<Company[]>('/api/v1/companies', {
    method: 'GET',
    auth: true,
  });
}

export async function getTransactions(): Promise<Transaction[]> {
  return request<Transaction[]>('/api/v1/transactions', {
    method: 'GET',
    auth: true,
  });
}

export async function getReportSummary(params: {
  company_id: number;
  start?: string;
  end?: string;
}): Promise<ReportSummaryResponse> {
  return request<ReportSummaryResponse>(
    `/api/v1/reports/summary${buildQuery(params)}`,
    {
      method: 'GET',
      auth: true,
    }
  );
}

export async function getReportContext(params: {
  company_id: number;
  start?: string;
  end?: string;
  limit?: number;
}): Promise<ReportContextResponse> {
  return request<ReportContextResponse>(
    `/api/v1/reports/context${buildQuery(params)}`,
    {
      method: 'GET',
      auth: true,
    }
  );
}
