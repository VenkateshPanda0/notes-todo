import { notifyItemsChanged } from "../lib/events";
import type {
  AIAnswer,
  AIPlan,
  AutoBackupList,
  ImportResult,
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

/** A write that changes items: same as request(), then tells the app that items changed. */
async function mutate<T>(path: string, options: RequestInit): Promise<T> {
  const result = await request<T>(path, options);
  notifyItemsChanged();
  return result;
}

// --- Auth / app lock -------------------------------------------------

export interface LockStatus {
  is_locked: boolean;
  /** The database file itself is encrypted (it cannot be opened without the password). */
  encrypted: boolean;
  /** This build can encrypt the database file. */
  encryption_available: boolean;
}

export interface EncryptionResult {
  encrypted: boolean;
  removed_plain_backups: number;
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
  enableEncryption: (password: string) =>
    request<EncryptionResult>("/api/auth/encryption/enable", {
      method: "POST",
      body: JSON.stringify({ password }),
    }),
  disableEncryption: (password: string) =>
    request<EncryptionResult>("/api/auth/encryption/disable", {
      method: "POST",
      body: JSON.stringify({ password }),
    }),
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
    mutate<Item>("/api/items", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  update: (id: number, payload: ItemUpdatePayload) =>
    mutate<Item>(`/api/items/${id}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    }),
  remove: (id: number) =>
    mutate<void>(`/api/items/${id}`, { method: "DELETE" }),
  complete: (id: number) =>
    mutate<Item>(`/api/items/${id}/complete`, { method: "POST" }),
  reopen: (id: number) =>
    mutate<Item>(`/api/items/${id}/reopen`, { method: "POST" }),
  convert: (id: number) =>
    mutate<Item>(`/api/items/${id}/convert`, { method: "POST" }),
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
  ask: (question: string) =>
    request<AIAnswer>("/api/ai/ask", { method: "POST", body: JSON.stringify({ question }) }),
  related: (id: number, limit = 5) => request<AIRelated[]>(`/api/ai/related/${id}?limit=${limit}`),
};

// --- Backup, export and import -------------------------------------------

/** Download a file from the API. A plain link can't send the session token, so fetch it first. */
async function downloadFile(path: string, fallbackName: string): Promise<void> {
  const headers: Record<string, string> = {};
  if (sessionToken) headers.Authorization = `Bearer ${sessionToken}`;
  const response = await fetch(`${BASE_URL}${path}`, { headers });
  if (response.status === 401) {
    sessionToken = null;
    unauthorizedHandler?.();
  }
  if (!response.ok) {
    let detail = response.statusText;
    try {
      detail = (await response.json()).detail ?? detail;
    } catch {
      // keep statusText
    }
    throw new Error(detail);
  }
  const disposition = response.headers.get("Content-Disposition") ?? "";
  const filename = /filename="([^"]+)"/.exec(disposition)?.[1] ?? fallbackName;
  const url = URL.createObjectURL(await response.blob());
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(url), 10_000);
}

export const backupApi = {
  exportJson: () => downloadFile("/api/backup/export.json", "taskflow-export.json"),
  exportMarkdown: () => downloadFile("/api/backup/export.zip", "taskflow-markdown.zip"),
  downloadDatabase: () => downloadFile("/api/backup/database", "taskflow.db"),
  importFile: (file: File, mode: "merge" | "replace") =>
    mutate<ImportResult>(`/api/backup/import?mode=${mode}`, { method: "POST", body: file }),
  auto: () => request<AutoBackupList>("/api/backup/auto"),
  runAuto: () => request<AutoBackupList>("/api/backup/auto/run", { method: "POST" }),
};
