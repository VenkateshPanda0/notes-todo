import type { Item } from "../types/item";

export function makeItem(overrides: Partial<Item> = {}): Item {
  return {
    id: 1,
    title: "Pay rent",
    content: "",
    type: "TODO",
    completed: false,
    priority: "HIGH",
    due_date: "2026-11-01",
    tags: [],
    created_at: "2026-10-01T00:00:00",
    updated_at: "2026-10-01T00:00:00",
    ...overrides,
  };
}
