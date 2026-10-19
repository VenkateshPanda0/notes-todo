import type {
  AIPlan,
  AIRelated,
  AISettingsUpdate,
  AIStatus,
  AISummary,
  GraphData,
  Item,
  ItemCreatePayload,
  ItemUpdatePayload,
  QuickAddPreview,
} from "../types/item";

// The packaged app serves the UI and API from the same local server on a free port, so production
// builds use relative URLs. During development the Vite dev server talks to the API on port 8000.
const BASE_URL: string =
  import.meta.env.VITE_API_URL ?? (import.meta.env.PROD ? "" : "http://127.0.0.1:8000");

// The session token lives in memory only: closing the app locks it again, and
// nothing sensitive is written to localStorage.
let sessionToken: string | null = null;
let unauthorizedHandler: (() => void) | null = null;

export function setUnauthorizedHandler(handler: (() => void) | null) {
  unauthorizedHandler = handler;
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (sessionToken) headers.Authorization = `Bearer ${sessionToken}`;

  const response = await fetch(`${BASE_URL}${path}`, { ...options, headers });

  if (response.status === 401 && !path.startsWith("/api/auth/")) {
    // The session expired or was revoked: send the user back to the lock screen.
    sessionToken = null;
    unauthorizedHandler?.();
  }

  if (!response.ok) {
    let detail = response.statusText;
    try {
      const body = await response.json();
      detail = body.detail ?? detail;
    } catch {
      // ignore parse failure, use statusText
    }
    throw new Error(detail);
  }

  if (response.status === 204) {
    return undefined as T;
  }
  return (await response.json()) as T;
}

// --- Auth / app lock -------------------------------------------------

export interface LockStatus {
  is_locked: boolean;
}

interface SessionToken {
  token: string;
}

async function startSession(path: string, body: object): Promise<void> {
  const { token } = await request<SessionToken>(path, {
    method: "POST",
    body: JSON.stringify(body),
  });
  sessionToken = token;
}

export const authApi = {
  status: () => request<LockStatus>("/api/auth/status"),
  setup: (password: string) => startSession("/api/auth/setup", { password }),
  unlock: (password: string) => startSession("/api/auth/unlock", { password }),
  changePassword: (current_password: string, new_password: string) =>
    startSession("/api/auth/change-password", { current_password, new_password }),
  lock: async () => {
    try {
      await request<void>("/api/auth/lock", { method: "POST" });
    } finally {
      sessionToken = null;
    }
  },
};

// --- Items -------------------------------------------------------------

export const itemsApi = {
  list: (params?: { type?: string; completed?: boolean; tag?: string }) => {
    const search = new URLSearchParams();
    if (params?.type) search.set("type", params.type);
    if (params?.completed !== undefined)
      search.set("completed", String(params.completed));
    if (params?.tag) search.set("tag", params.tag);
    const qs = search.toString();
    return request<Item[]>(`/api/items${qs ? `?${qs}` : ""}`);
  },
  get: (id: number) => request<Item>(`/api/items/${id}`),
  backlinks: (id: number) => request<Item[]>(`/api/items/${id}/backlinks`),
  parse: (text: string) =>
    request<QuickAddPreview>("/api/items/parse", {
      method: "POST",
      body: JSON.stringify({ text }),
    }),
  create: (payload: ItemCreatePayload) =>
    request<Item>("/api/items", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  update: (id: number, payload: ItemUpdatePayload) =>
    request<Item>(`/api/items/${id}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    }),
  remove: (id: number) =>
    request<void>(`/api/items/${id}`, { method: "DELETE" }),
  complete: (id: number) =>
    request<Item>(`/api/items/${id}/complete`, { method: "POST" }),
  reopen: (id: number) =>
    request<Item>(`/api/items/${id}/reopen`, { method: "POST" }),
  convert: (id: number) =>
    request<Item>(`/api/items/${id}/convert`, { method: "POST" }),
};

// --- Graph -------------------------------------------------------------

export const graphApi = {
  get: () => request<GraphData>("/api/graph"),
};

// --- Local AI (Ollama) ---------------------------------------------------

export const aiApi = {
  status: () => request<AIStatus>("/api/ai/status"),
  updateSettings: (payload: AISettingsUpdate) =>
    request<AIStatus>("/api/ai/settings", {
      method: "PUT",
      body: JSON.stringify(payload),
    }),
  summarize: (id: number) => request<AISummary>(`/api/ai/summarize/${id}`, { method: "POST" }),
  planDay: () => request<AIPlan>("/api/ai/plan-day", { method: "POST" }),
  related: (id: number, limit = 5) => request<AIRelated[]>(`/api/ai/related/${id}?limit=${limit}`),
};
