import { useEffect, useMemo, useState } from "react";
import { itemsApi } from "../api/client";
import { Button } from "../components/Button";
import { TaskModal } from "../components/TaskModal";
import type { Item, ItemType, Priority } from "../types/item";

const WEEKDAY_LABELS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

function toDateKey(d: Date): string {
  const year = d.getFullYear();
  const month = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function isSameDay(a: Date, b: Date): boolean {
  return toDateKey(a) === toDateKey(b);
}

const PRIORITY_DOT: Record<Priority, string> = {
  HIGH: "bg-danger",
  MEDIUM: "bg-amber-400",
  LOW: "bg-[var(--text-secondary)]",
};

export function CalendarView() {
  const [items, setItems] = useState<Item[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [cursor, setCursor] = useState(() => {
    const now = new Date();
    return new Date(now.getFullYear(), now.getMonth(), 1);
  });
  const [modalOpen, setModalOpen] = useState(false);
  const [editingItem, setEditingItem] = useState<Item | null>(null);
  const [prefillDate, setPrefillDate] = useState<string | null>(null);

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await itemsApi.list({ type: "TODO" });
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

  const itemsByDay = useMemo(() => {
    const map = new Map<string, Item[]>();
    for (const item of items) {
      if (!item.due_date) continue;
      const list = map.get(item.due_date) ?? [];
      list.push(item);
      map.set(item.due_date, list);
    }
    return map;
  }, [items]);

  const weeks = useMemo(() => {
    const firstOfMonth = cursor;
    const startDay = firstOfMonth.getDay(); // 0 = Sun
    const gridStart = new Date(firstOfMonth);
    gridStart.setDate(gridStart.getDate() - startDay);

    const days: Date[] = [];
    for (let i = 0; i < 42; i++) {
      const d = new Date(gridStart);
      d.setDate(gridStart.getDate() + i);
      days.push(d);
    }

    const result: Date[][] = [];
    for (let i = 0; i < days.length; i += 7) {
      result.push(days.slice(i, i + 7));
    }
    return result;
  }, [cursor]);

  const monthLabel = cursor.toLocaleDateString(undefined, {
    month: "long",
    year: "numeric",
  });

  const today = new Date();

  const goPrevMonth = () =>
    setCursor((c) => new Date(c.getFullYear(), c.getMonth() - 1, 1));
  const goNextMonth = () =>
    setCursor((c) => new Date(c.getFullYear(), c.getMonth() + 1, 1));
  const goToday = () => {
    const now = new Date();
    setCursor(new Date(now.getFullYear(), now.getMonth(), 1));
  };

  const handleOpenNewOnDay = (day: Date) => {
    setEditingItem(null);
    setPrefillDate(toDateKey(day));
    setModalOpen(true);
  };

  const handleOpenEdit = (item: Item) => {
    setEditingItem(item);
    setPrefillDate(null);
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

  const modalInitial: Item | null = editingItem
    ? editingItem
    : prefillDate
      ? ({
          id: -1,
          title: "",
          content: "",
          type: "TODO",
          completed: false,
          priority: "MEDIUM",
          due_date: prefillDate,
          created_at: "",
          updated_at: "",
        } as Item)
      : null;

  return (
    <div className="mx-auto max-w-5xl px-6 py-8">
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-semibold text-[var(--text)]">
          Calendar
        </h1>
        <Button
          onClick={() => {
            setEditingItem(null);
            setPrefillDate(null);
            setModalOpen(true);
          }}
        >
          + Add Task
        </Button>
      </div>

      <div className="mb-4 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <button
            onClick={goPrevMonth}
            aria-label="Previous month"
            className="rounded-lg border border-[var(--border)] px-2 py-1 text-sm text-[var(--text-secondary)] hover:bg-[var(--border)]/40"
          >
            ‹
          </button>
          <button
            onClick={goNextMonth}
            aria-label="Next month"
            className="rounded-lg border border-[var(--border)] px-2 py-1 text-sm text-[var(--text-secondary)] hover:bg-[var(--border)]/40"
          >
            ›
          </button>
          <button
            onClick={goToday}
            className="rounded-lg border border-[var(--border)] px-3 py-1 text-sm text-[var(--text-secondary)] hover:bg-[var(--border)]/40"
          >
            Today
          </button>
        </div>
        <span className="text-sm font-medium text-[var(--text)]">
          {monthLabel}
        </span>
      </div>

      {error && <p className="py-4 text-sm text-danger">{error}</p>}
      {loading && (
        <p className="py-8 text-center text-sm text-[var(--text-secondary)]">
          Loading...
        </p>
      )}

      {!loading && !error && (
        <div className="overflow-hidden rounded-xl border border-[var(--border)]">
          <div className="grid grid-cols-7 border-b border-[var(--border)] bg-[var(--bg-elevated)]">
            {WEEKDAY_LABELS.map((label) => (
              <div
                key={label}
                className="px-2 py-2 text-center text-xs font-medium text-[var(--text-secondary)]"
              >
                {label}
              </div>
            ))}
          </div>

          {weeks.map((week, wi) => (
            <div
              key={wi}
              className="grid grid-cols-7 border-b border-[var(--border)] last:border-b-0"
            >
              {week.map((day) => {
                const inMonth = day.getMonth() === cursor.getMonth();
                const key = toDateKey(day);
                const dayItems = itemsByDay.get(key) ?? [];
                const visible = dayItems.slice(0, 3);
                const overflow = dayItems.length - visible.length;

                return (
                  <div
                    key={key}
                    onClick={() => handleOpenNewOnDay(day)}
                    className={`min-h-[110px] cursor-pointer border-r border-[var(--border)] p-2 last:border-r-0 hover:bg-[var(--border)]/20 ${
                      inMonth ? "" : "opacity-40"
                    }`}
                  >
                    <div
                      className={`mb-1 inline-flex h-6 w-6 items-center justify-center rounded-full text-xs ${
                        isSameDay(day, today)
                          ? "bg-primary text-white"
                          : "text-[var(--text-secondary)]"
                      }`}
                    >
                      {day.getDate()}
                    </div>
                    <div className="space-y-1">
                      {visible.map((item) => (
                        <div
                          key={item.id}
                          onClick={(e) => {
                            e.stopPropagation();
                            handleOpenEdit(item);
                          }}
                          className={`flex items-center gap-1 truncate rounded px-1.5 py-0.5 text-xs ${
                            item.completed
                              ? "text-[var(--text-secondary)] line-through"
                              : "bg-primary/10 text-primary"
                          }`}
                          title={item.title}
                        >
                          <span
                            className={`h-1.5 w-1.5 shrink-0 rounded-full ${PRIORITY_DOT[item.priority]}`}
                          />
                          <span className="truncate">{item.title}</span>
                        </div>
                      ))}
                      {overflow > 0 && (
                        <div className="px-1.5 text-xs text-[var(--text-secondary)]">
                          +{overflow} more
                        </div>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          ))}
        </div>
      )}

      <TaskModal
        open={modalOpen}
        initial={modalInitial}
        defaultType="TODO"
        onClose={() => setModalOpen(false)}
        onSave={handleSave}
        onDelete={editingItem ? handleDelete : undefined}
      />
    </div>
  );
}
