import { useEffect, useMemo, useRef, useState } from "react";
import { itemsApi } from "../api/client";
import { Button } from "../components/Button";
import { Input } from "../components/Input";
import { PlanMyDay } from "../components/PlanMyDay";
import { QuickAdd } from "../components/QuickAdd";
import { TaskModal } from "../components/TaskModal";
import { TaskRow } from "../components/TaskRow";
import { isToday, isUpcoming } from "../lib/dates";
import { normalizeTitle } from "../lib/markdown";
import type { Item, ItemType, Priority } from "../types/item";

type Filter = "all" | "active" | "completed";

interface DashboardProps {
  view?: "all" | "today" | "upcoming" | "completed" | "notes";
}

export function Dashboard({ view = "all" }: DashboardProps) {
  const [items, setItems] = useState<Item[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [filter, setFilter] = useState<Filter>("all");
  const [activeTag, setActiveTag] = useState<string | null>(null);
  const [modalOpen, setModalOpen] = useState(false);
  const [editingItem, setEditingItem] = useState<Item | null>(null);

  const quickAddRef = useRef<HTMLInputElement>(null);

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

  // Keyboard shortcuts: "/" focuses quick add, "n" opens the full form. Ignored while typing.
  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.ctrlKey || e.metaKey || e.altKey || modalOpen) return;
      const el = document.activeElement;
      if (
        el instanceof HTMLElement &&
        (el.isContentEditable || ["INPUT", "TEXTAREA", "SELECT"].includes(el.tagName))
      ) {
        return;
      }
      if (e.key === "/") {
        e.preventDefault();
        quickAddRef.current?.focus();
      } else if (e.key === "n") {
        e.preventDefault();
        setEditingItem(null);
        setModalOpen(true);
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [modalOpen]);

  // Tags in use among the items this view is about (notes, or todos), with counts.
  const tagCounts = useMemo(() => {
    const wanted = view === "notes" ? "NOTE" : "TODO";
    const counts = new Map<string, number>();
    for (const item of items) {
      if (item.type !== wanted) continue;
      for (const tag of item.tags) counts.set(tag, (counts.get(tag) ?? 0) + 1);
    }
    return [...counts.entries()].sort((a, b) => a[0].localeCompare(b[0]));
  }, [items, view]);

  // A selected tag that no longer exists (e.g. its last item was retagged) stops filtering.
  const effectiveTag =
    activeTag && tagCounts.some(([tag]) => tag === activeTag) ? activeTag : null;

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

    if (effectiveTag) {
      result = result.filter((i) => i.tags.includes(effectiveTag));
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
  }, [items, view, filter, search, effectiveTag]);

  const knownTitles = useMemo(
    () => new Set(items.map((i) => normalizeTitle(i.title))),
    [items],
  );

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
    // Completing a repeating todo creates its next occurrence on the server; fetch it.
    if (updated.completed && updated.recurrence) await load();
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
    recurrence: string | null;
    tags: string[];
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

  // Follow a [[link]]: open the item with that title, or create a note for it if none exists.
  const handleOpenLink = async (linkTitle: string) => {
    const target = normalizeTitle(linkTitle);
    let found = items.find((i) => normalizeTitle(i.title) === target);
    if (!found) {
      try {
        found = await itemsApi.create({ title: linkTitle.trim(), type: "NOTE" });
        const created = found;
        setItems((prev) => [created, ...prev]);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Could not create note.");
        return;
      }
    }
    setEditingItem(found);
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

      {(view === "today" || view === "all") && (
        <PlanMyDay
          onOpenItem={(item) => {
            setEditingItem(item);
            setModalOpen(true);
          }}
        />
      )}

      {view !== "completed" && (
        <QuickAdd
          defaultType={view === "notes" ? "NOTE" : "TODO"}
          inputRef={quickAddRef}
          onCreated={(created) => setItems((prev) => [created, ...prev])}
        />
      )}

      <Input
        value={search}
        onChange={(e) => setSearch(e.target.value)}
        placeholder="Search tasks..."
        className="mb-4"
      />

      {tagCounts.length > 0 && (
        <div className="mb-4 flex flex-wrap items-center gap-2" aria-label="Filter by tag">
          {tagCounts.map(([tag, count]) => (
            <button
              key={tag}
              onClick={() => setActiveTag(effectiveTag === tag ? null : tag)}
              className={`rounded-full px-3 py-1 text-xs font-medium transition-colors ${
                effectiveTag === tag
                  ? "bg-primary text-white"
                  : "bg-primary/10 text-primary-ink hover:bg-primary/20"
              }`}
            >
              #{tag} <span className="opacity-70">{count}</span>
            </button>
          ))}
          {effectiveTag && (
            <button
              onClick={() => setActiveTag(null)}
              className="text-xs text-[var(--text-secondary)] underline"
            >
              Clear
            </button>
          )}
        </div>
      )}

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

      {error && <p className="py-4 text-sm text-danger-ink">{error}</p>}

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
        knownTitles={knownTitles}
        onOpenLink={handleOpenLink}
        onOpenItem={(item) => setEditingItem(item)}
        onClose={() => setModalOpen(false)}
        onSave={handleSave}
        onDelete={editingItem ? handleDelete : undefined}
      />
    </div>
  );
}
