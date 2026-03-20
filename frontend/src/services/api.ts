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

    if (!token) {
      clearToken();

      if (typeof window !== 'undefined' && window.location.pathname !== '/login') {
        window.location.href = '/login';
      }

      throw new Error('Sessão expirada. Faça login novamente.');
    }

    finalHeaders.set('Authorization', `Bearer ${token}`);
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

export type CreateCompanyPayload = {
  cnpj: string;
  razao_social: string;
};

export async function createCompany(payload: CreateCompanyPayload): Promise<Company> {
  return request<Company>('/api/v1/companies', {
    method: 'POST',
    auth: true,
    body: JSON.stringify(payload),
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

export type AIConsultNumbers = {
  entradas_cents: number;
  saidas_cents: number;
  saldo_cents: number;
  qtd_transacoes: number;
};

export type AIConsultTopCategory = {
  category_id?: number | null;
  category_name: string;
  entradas_cents: number;
  saidas_cents: number;
  saldo_cents: number;
  qtd_transacoes: number;
};

export type AIConsultRecentTransaction = {
  id: number;
  occurred_at?: string | null;
  kind: string;
  amount_cents: number;
  category_id?: number | null;
  category_name: string;
  description: string;
};

export type AIConsultResponse = {
  company_id: number;
  period: ReportPeriod;
  generated_at: string;
  headline: string;
  insights: string[];
  risks: string[];
  actions: string[];
  numbers: AIConsultNumbers;
  top_categories: AIConsultTopCategory[];
  recent_transactions: AIConsultRecentTransaction[];
};

export async function getAIConsult(params: {
  company_id: number;
  start?: string;
  end?: string;
  limit?: number;
  question?: string;
}): Promise<AIConsultResponse> {
  const payload = {
    company_id: params.company_id,
    period: {
      start: params.start,
      end: params.end,
    },
    limit: params.limit ?? 20,
    ...(params.question ? { question: params.question } : {}),
  };

  return request<AIConsultResponse>('/api/v1/ai/consult', {
    method: 'POST',
    auth: true,
    body: JSON.stringify(payload),
  });
}

export async function openAIConsultPdf(params: {
  company_id: number;
  start?: string;
  end?: string;
  limit?: number;
  question?: string;
}): Promise<void> {
  const token = getToken();

  if (!token) {
    clearToken();

    if (typeof window !== 'undefined' && window.location.pathname !== '/login') {
      window.location.href = '/login';
    }

    throw new Error('Sessão expirada. Faça login novamente.');
  }

  const payload = {
    company_id: params.company_id,
    period: {
      start: params.start,
      end: params.end,
    },
    limit: params.limit ?? 20,
    ...(params.question ? { question: params.question } : {}),
  };

  const response = await fetch(`${API_BASE_URL}/api/v1/reports/ai-consult/pdf`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    let message = 'Erro ao gerar PDF executivo';

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

    throw new Error(typeof message === 'string' ? message : 'Erro ao gerar PDF executivo');
  }

  const blob = await response.blob();
  const fileUrl = window.URL.createObjectURL(blob);
  const opened = window.open(fileUrl, '_blank', 'noopener,noreferrer');

  if (!opened) {
    const link = document.createElement('a');
    link.href = fileUrl;
    link.download = 'ia-cnpj-relatorio-ai-consult.pdf';
    document.body.appendChild(link);
    link.click();
    link.remove();
  }

  window.setTimeout(() => {
    window.URL.revokeObjectURL(fileUrl);
  }, 60000);
}
