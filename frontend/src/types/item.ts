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
