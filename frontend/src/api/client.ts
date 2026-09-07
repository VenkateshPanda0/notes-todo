import type { Item, ItemCreatePayload, ItemUpdatePayload } from "../types/item";

const BASE_URL = import.meta.env.VITE_API_URL ?? "http://127.0.0.1:8000";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });

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

export const authApi = {
  status: () => request<LockStatus>("/api/auth/status"),
  setup: (password: string) =>
    request<void>("/api/auth/setup", {
      method: "POST",
      body: JSON.stringify({ password }),
    }),
  unlock: (password: string) =>
    request<void>("/api/auth/unlock", {
      method: "POST",
      body: JSON.stringify({ password }),
    }),
  changePassword: (current_password: string, new_password: string) =>
    request<void>("/api/auth/change-password", {
      method: "POST",
      body: JSON.stringify({ current_password, new_password }),
    }),
};

// --- Items -------------------------------------------------------------

export const itemsApi = {
  list: (params?: { type?: string; completed?: boolean }) => {
    const search = new URLSearchParams();
    if (params?.type) search.set("type", params.type);
    if (params?.completed !== undefined)
      search.set("completed", String(params.completed));
    const qs = search.toString();
    return request<Item[]>(`/api/items${qs ? `?${qs}` : ""}`);
  },
  get: (id: number) => request<Item>(`/api/items/${id}`),
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
