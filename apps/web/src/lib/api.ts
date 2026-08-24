/**
 * API client for Nexora AI Backend
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

async function getToken(): Promise<string | null> {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("token");
}

async function request<T = any>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const token = await getToken();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string> || {}),
  };
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers,
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ error: "Request failed" }));
    throw new Error(err.error || err.detail || `HTTP ${res.status}`);
  }

  return res.json();
}

// ---------------------------------------------------------------------------
// Orchestrator API
// ---------------------------------------------------------------------------

export async function orchestrate(params: {
  message: string;
  chat_id?: string;
  document_ids?: string[];
  metadata?: Record<string, any>;
}) {
  return request("/orchestrator/orchestrate", {
    method: "POST",
    body: JSON.stringify(params),
  });
}

export async function getTrace(traceId: string) {
  return request(`/orchestrator/orchestrate/trace/${traceId}`);
}

export async function getTimeline(traceId: string) {
  return request(`/orchestrator/orchestrate/trace/${traceId}/timeline`);
}

export async function listTraces(limit = 20) {
  return request(`/orchestrator/orchestrate/traces?limit=${limit}`);
}

// ---------------------------------------------------------------------------
// Approvals API
// ---------------------------------------------------------------------------

export async function listApprovals() {
  return request("/orchestrator/orchestrate/approvals");
}

export async function approveAction(requestId: string, reason = "") {
  return request(`/orchestrator/orchestrate/approve/${requestId}`, {
    method: "POST",
    body: JSON.stringify({ reason }),
  });
}

export async function rejectAction(requestId: string, reason = "") {
  return request(`/orchestrator/orchestrate/reject/${requestId}`, {
    method: "POST",
    body: JSON.stringify({ reason }),
  });
}

// ---------------------------------------------------------------------------
// Models API
// ---------------------------------------------------------------------------

export async function listModels(provider?: string) {
  const q = provider ? `?provider=${provider}` : "";
  return request(`/orchestrator/orchestrate/models${q}`);
}

export async function routeModel(params: {
  task_type?: string;
  user_input?: string;
}) {
  return request("/orchestrator/orchestrate/route", {
    method: "POST",
    body: JSON.stringify(params),
  });
}

// ---------------------------------------------------------------------------
// Usage API
// ---------------------------------------------------------------------------

export async function getUsageSummary(days = 30) {
  return request(`/orchestrator/orchestrate/usage?days=${days}`);
}

// ---------------------------------------------------------------------------
// Agents API
// ---------------------------------------------------------------------------

export async function listAgentCatalog() {
  return request("/orchestrator/orchestrate/catalog");
}

export async function listCompanyAgents(page = 1, pageSize = 20) {
  return request(`/agents?page=${page}&page_size=${pageSize}`);
}

// ---------------------------------------------------------------------------
// Chat API (simple)
// ---------------------------------------------------------------------------

export async function sendChat(message: string, history: any[] = []) {
  const res = await fetch(`${API_BASE.replace("/api/v1", "")}/api/chat`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(await getToken() ? { Authorization: `Bearer ${await getToken()}` } : {}),
    },
    body: JSON.stringify({ message, history }),
  });
  return res.json();
}
