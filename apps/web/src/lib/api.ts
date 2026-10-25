/**
 * API client for Nexora AI Backend
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

let refreshInFlight: Promise<string | null> | null = null;

async function getToken(): Promise<string | null> {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("token");
}

function expireLocalSession() {
  if (typeof window === "undefined") return;
  localStorage.removeItem("token");
  localStorage.removeItem("refresh_token");
  window.dispatchEvent(new Event("nexora:auth-expired"));
}

async function refreshAccessToken(): Promise<string | null> {
  if (refreshInFlight) return refreshInFlight;
  refreshInFlight = (async () => {
    const refreshToken = typeof window === "undefined"
      ? null
      : localStorage.getItem("refresh_token");
    if (!refreshToken) return null;

    try {
      const response = await fetch(`${API_BASE}/auth/refresh`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token: refreshToken }),
      });
      if (!response.ok) return null;
      const data = await response.json();
      if (!data.access_token || !data.refresh_token) return null;
      localStorage.setItem("token", data.access_token);
      localStorage.setItem("refresh_token", data.refresh_token);
      return data.access_token as string;
    } catch {
      return null;
    } finally {
      refreshInFlight = null;
    }
  })();
  return refreshInFlight;
}

async function readResponse<T>(response: Response): Promise<T> {
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(data.error || data.detail || `HTTP ${response.status}`);
  }
  return data as T;
}

export async function loginRequest(email: string, password: string) {
  const response = await fetch(`${API_BASE}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  return readResponse<{
    access_token: string;
    refresh_token: string;
    requires_mfa: boolean;
    user: Record<string, any>;
  }>(response);
}

export async function registerRequest(input: {
  first_name: string;
  last_name: string;
  company_name: string;
  email: string;
  password: string;
}) {
  const response = await fetch(`${API_BASE}/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
  return readResponse<{
    access_token: string;
    refresh_token: string;
    user: Record<string, any>;
  }>(response);
}

export async function verifyMfaRequest(userId: string, code: string) {
  const response = await fetch(`${API_BASE}/auth/mfa/verify`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ user_id: userId, code }),
  });
  return readResponse<{
    access_token: string;
    refresh_token: string;
    user: Record<string, any>;
  }>(response);
}

export async function revokeAuthSession() {
  return request<{ success: boolean }>("/auth/logout", {
    method: "POST",
    body: JSON.stringify({}),
  });
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

  const url = `${API_BASE}${path}`;
  let res = await fetch(url, {
    ...options,
    headers,
  });

  if (res.status === 401) {
    const newToken = await refreshAccessToken();
    if (newToken) {
      headers.Authorization = `Bearer ${newToken}`;
      res = await fetch(url, { ...options, headers });
    } else {
      expireLocalSession();
    }
  }

  return readResponse<T>(res);
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

export interface PersistentChatMessage {
  id: string;
  chat_id: string;
  role: "user" | "assistant";
  content: string;
  created_at: string;
  attachment_name?: string | null;
  sources?: Array<{ id?: string; name?: string; detail?: string }>;
  legacy_timestamp?: string | null;
}

export async function getOrCreatePersistentChat() {
  return request<{ id: string; message_count: number }>("/chats/persistent", {
    method: "POST",
    body: JSON.stringify({}),
  });
}

export async function getPersistentChatMessages(chatId: string, page = 1) {
  return request<{
    total: number;
    page: number;
    page_size: number;
    items: PersistentChatMessage[];
  }>(`/chats/${chatId}/messages?page=${page}&page_size=200`);
}

export async function importLegacyChatHistory(
  chatId: string,
  messages: Array<{
    id: string;
    role: "user" | "ai" | "assistant";
    text: string;
    timestamp?: string;
    attachment_name?: string;
    sources?: Array<{ id?: string; name?: string; detail?: string }>;
  }>,
) {
  return request<{ imported: number; already_exists: boolean }>(
    `/chats/${chatId}/history/import`,
    { method: "POST", body: JSON.stringify({ messages }) },
  );
}

export async function sendPersistentChatMessage(
  chatId: string,
  content: string,
  attachmentName?: string | null,
) {
  return request<{
    message: PersistentChatMessage;
    ai_message: PersistentChatMessage;
    chat_id: string;
  }>(`/chats/${chatId}/messages`, {
    method: "POST",
    body: JSON.stringify({ content, attachment_name: attachmentName || null }),
  });
}
