export type ItemType = "TODO" | "NOTE";
export type Priority = "LOW" | "MEDIUM" | "HIGH";

export interface Item {
  id: number;
  title: string;
  content: string;
  type: ItemType;
  completed: boolean;
  priority: Priority;
  due_date: string | null;
  tags: string[];
  created_at: string;
  updated_at: string;
}

export interface ItemCreatePayload {
  title: string;
  content?: string;
  type: ItemType;
  priority?: Priority;
  due_date?: string | null;
  tags?: string[];
}

export interface ItemUpdatePayload {
  title?: string;
  content?: string;
  type?: ItemType;
  completed?: boolean;
  priority?: Priority;
  due_date?: string | null;
  tags?: string[];
}

export interface QuickAddPreview {
  title: string;
  type: ItemType;
  priority: Priority;
  due_date: string | null;
  tags: string[];
}

export interface GraphNodeData {
  key: string;
  id: number | null;
  title: string;
  type: ItemType | null;
  completed: boolean;
  tags: string[];
  missing: boolean;
  degree: number;
}

export interface GraphData {
  nodes: GraphNodeData[];
  edges: { source: string; target: string }[];
}

export interface AIStatus {
  enabled: boolean;
  available: boolean;
  local: boolean;
  base_url: string;
  models: string[];
  model: string;
  embed_model: string;
  chat_model_ready: boolean;
  embed_model_ready: boolean;
  error: string | null;
}

export interface AISettingsUpdate {
  enabled?: boolean;
  model?: string;
  embed_model?: string;
}

export interface AISummary {
  summary: string;
  model: string;
}

export interface AIPlan {
  plan: string;
  model: string;
  items: Item[];
}

export interface AIRelated {
  item: Item;
  score: number;
}

export interface ImportResult {
  mode: "merge" | "replace";
  imported: number;
  skipped: number;
}

export interface AutoBackupList {
  enabled: boolean;
  directory: string | null;
  backups: { name: string; size: number; modified: string }[];
}

export interface AIAnswer {
  answer: string;
  model: string;
  sources: AIRelated[];
}
