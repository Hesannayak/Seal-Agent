// ── API client for Seal-Agent backend ──

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const url = `${API_BASE}${path}`;
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options?.headers as Record<string, string>),
  };

  const token =
    typeof window !== "undefined" ? localStorage.getItem("seal_api_key") : null;
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const res = await fetch(url, { ...options, headers });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`API ${res.status}: ${body}`);
  }
  return res.json();
}

// ── Prospects ──

export const prospects = {
  list: (params?: { status?: string; limit?: number }) =>
    request<{ prospects: any[]; total: number }>(
      `/api/prospects?${new URLSearchParams(params as any)}`
    ),
  get: (id: string) => request<any>(`/api/prospects/${id}`),
  create: (data: any) =>
    request<any>("/api/prospects", {
      method: "POST",
      body: JSON.stringify(data),
    }),
};

// ── Deals ──

export const deals = {
  list: () => request<{ deals: any[]; total: number }>("/api/deals"),
  get: (id: string) => request<any>(`/api/deals/${id}`),
  create: (data: any) =>
    request<any>("/api/deals", { method: "POST", body: JSON.stringify(data) }),
  pipeline: () => request<any>("/api/deals/pipeline"),
  forecast: () => request<any>("/api/deals/forecast"),
  atRisk: () => request<any>("/api/deals/at-risk"),
};

// ── Analytics ──

export const analytics = {
  pipeline: () => request<any>("/api/analytics/pipeline"),
  activity: (days = 30) => request<any>(`/api/analytics/activity?days=${days}`),
  funnel: () => request<any>("/api/analytics/funnel"),
  forecast: () => request<any>("/api/analytics/forecast"),
  report: (days = 30) => request<any>(`/api/analytics/report?days=${days}`),
};

// ── Agent ──

export const agent = {
  status: () => request<any>("/api/agent/status"),
  chat: (message: string) =>
    request<any>("/api/agent/chat", {
      method: "POST",
      body: JSON.stringify({ message }),
    }),
};

// ── Integrations ──

export const integrations = {
  list: () => request<{ integrations: any[]; count: number }>("/api/integrations/"),
  connect: (name: string, credentials: Record<string, string>) =>
    request<any>(`/api/integrations/${name}/connect`, {
      method: "POST",
      body: JSON.stringify({ credentials }),
    }),
  disconnect: (name: string) =>
    request<any>(`/api/integrations/${name}/disconnect`, { method: "POST" }),
  health: (name: string) => request<any>(`/api/integrations/${name}/health`),
};

// ── Health ──

export const health = () => request<{ status: string; agent: string }>("/health");
