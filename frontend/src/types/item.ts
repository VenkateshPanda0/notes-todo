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
  created_at: string;
  updated_at: string;
}

export interface ItemCreatePayload {
  title: string;
  content?: string;
  type: ItemType;
  priority?: Priority;
  due_date?: string | null;
}

export interface ItemUpdatePayload {
  title?: string;
  content?: string;
  type?: ItemType;
  completed?: boolean;
  priority?: Priority;
  due_date?: string | null;
}
