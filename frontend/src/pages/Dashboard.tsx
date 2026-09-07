import { useEffect, useMemo, useState } from "react";
import { itemsApi } from "../api/client";
import { Button } from "../components/Button";
import { Input } from "../components/Input";
import { TaskModal } from "../components/TaskModal";
import { TaskRow } from "../components/TaskRow";
import type { Item, ItemType, Priority } from "../types/item";

type Filter = "all" | "active" | "completed";

interface DashboardProps {
  view?: "all" | "today" | "upcoming" | "completed" | "notes";
}

function localDateString(d: Date): string {
  const year = d.getFullYear();
  const month = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function isToday(dateStr: string | null): boolean {
  if (!dateStr) return false;
  return dateStr === localDateString(new Date());
}

function isUpcoming(dateStr: string | null): boolean {
  if (!dateStr) return false;
  return dateStr > localDateString(new Date());
}

export function Dashboard({ view = "all" }: DashboardProps) {
  const [items, setItems] = useState<Item[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [filter, setFilter] = useState<Filter>("all");
  const [modalOpen, setModalOpen] = useState(false);
  const [editingItem, setEditingItem] = useState<Item | null>(null);

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await itemsApi.list();
      setItems(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load tasks.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const filtered = useMemo(() => {
    let result = items;

    if (view === "notes") {
      result = result.filter((i) => i.type === "NOTE");
    } else {
      // Todo-oriented views never show Notes
      result = result.filter((i) => i.type === "TODO");

      if (view === "today") {
        result = result.filter((i) => isToday(i.due_date));
      } else if (view === "upcoming") {
        result = result.filter((i) => isUpcoming(i.due_date));
      } else if (view === "completed") {
        result = result.filter((i) => i.completed);
      } else {
        if (filter === "active") result = result.filter((i) => !i.completed);
        if (filter === "completed") result = result.filter((i) => i.completed);
      }
    }

    if (search.trim()) {
      const q = search.toLowerCase();
      result = result.filter(
        (i) =>
          i.title.toLowerCase().includes(q) ||
          i.content.toLowerCase().includes(q),
      );
    }

    return result;
  }, [items, view, filter, search]);

  const title =
    view === "today"
      ? "Today"
      : view === "upcoming"
        ? "Upcoming"
        : view === "completed"
          ? "Completed"
          : view === "notes"
            ? "Notes"
            : "All Tasks";

  const handleToggleComplete = async (item: Item) => {
    const updated = item.completed
      ? await itemsApi.reopen(item.id)
      : await itemsApi.complete(item.id);
    setItems((prev) => prev.map((i) => (i.id === updated.id ? updated : i)));
  };

  const handleOpenNew = () => {
    setEditingItem(null);
    setModalOpen(true);
  };

  const handleOpenEdit = (item: Item) => {
    setEditingItem(item);
    setModalOpen(true);
  };

  const handleSave = async (data: {
    title: string;
    content: string;
    type: ItemType;
    priority: Priority;
    due_date: string | null;
  }) => {
    if (editingItem) {
      let updated = await itemsApi.update(editingItem.id, data);
      if (editingItem.type !== data.type) {
        updated = await itemsApi.convert(updated.id);
      }
      setItems((prev) => prev.map((i) => (i.id === updated.id ? updated : i)));
    } else {
      const created = await itemsApi.create(data);
      setItems((prev) => [created, ...prev]);
    }
  };

  const handleDelete = async () => {
    if (!editingItem) return;
    await itemsApi.remove(editingItem.id);
    setItems((prev) => prev.filter((i) => i.id !== editingItem.id));
    setModalOpen(false);
  };

  return (
    <div className="mx-auto max-w-3xl px-6 py-8">
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-semibold text-[var(--text)]">{title}</h1>
        <Button onClick={handleOpenNew}>+ Add Task</Button>
      </div>

      <Input
        value={search}
        onChange={(e) => setSearch(e.target.value)}
        placeholder="Search tasks..."
        className="mb-4"
      />

      {view === "all" && (
        <div className="mb-4 flex gap-2">
          {(["all", "active", "completed"] as Filter[]).map((f) => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={`rounded-full px-3 py-1 text-xs font-medium capitalize transition-colors ${
                filter === f
                  ? "bg-primary text-white"
                  : "bg-[var(--border)]/40 text-[var(--text-secondary)]"
              }`}
            >
              {f}
            </button>
          ))}
        </div>
      )}

      {loading && (
        <p className="py-8 text-center text-sm text-[var(--text-secondary)]">
          Loading...
        </p>
      )}

      {error && <p className="py-4 text-sm text-danger">{error}</p>}

      {!loading && !error && filtered.length === 0 && (
        <p className="py-12 text-center text-sm text-[var(--text-secondary)]">
          Nothing here yet.
        </p>
      )}

      <div className="space-y-2">
        {filtered.map((item) => (
          <TaskRow
            key={item.id}
            item={item}
            onToggleComplete={handleToggleComplete}
            onClick={handleOpenEdit}
          />
        ))}
      </div>

      <TaskModal
        open={modalOpen}
        initial={editingItem}
        defaultType={view === "notes" ? "NOTE" : "TODO"}
        onClose={() => setModalOpen(false)}
        onSave={handleSave}
        onDelete={editingItem ? handleDelete : undefined}
      />
    </div>
  );
}
