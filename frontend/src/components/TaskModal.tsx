import { useEffect, useState } from "react";
import type { Item, ItemType, Priority } from "../types/item";
import { Button } from "./Button";
import { Input } from "./Input";

interface TaskModalProps {
  open: boolean;
  initial?: Item | null;
  defaultType?: ItemType;
  onClose: () => void;
  onSave: (data: {
    title: string;
    content: string;
    type: ItemType;
    priority: Priority;
    due_date: string | null;
  }) => Promise<void>;
  onDelete?: () => Promise<void>;
}

export function TaskModal({
  open,
  initial,
  defaultType = "TODO",
  onClose,
  onSave,
  onDelete,
}: TaskModalProps) {
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const [type, setType] = useState<ItemType>("TODO");
  const [priority, setPriority] = useState<Priority>("MEDIUM");
  const [dueDate, setDueDate] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (open) {
      setTitle(initial?.title ?? "");
      setContent(initial?.content ?? "");
      setType(initial?.type ?? defaultType);
      setPriority(initial?.priority ?? "MEDIUM");
      setDueDate(initial?.due_date ?? "");
      setError(null);
    }
  }, [open, initial, defaultType]);

  if (!open) return null;

  const handleSave = async () => {
    if (!title.trim()) {
      setError("Title is required.");
      return;
    }
    setSaving(true);
    setError(null);
    try {
      await onSave({
        title: title.trim(),
        content,
        type,
        priority,
        due_date: dueDate || null,
      });
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <div className="w-full max-w-md rounded-xl border border-[var(--border)] bg-[var(--bg-elevated)] p-6 shadow-xl">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-[var(--text)]">
            {initial ? "Edit Task" : "Add Task"}
          </h2>
          <button
            onClick={onClose}
            className="text-[var(--text-secondary)] hover:text-[var(--text)]"
            aria-label="Close"
          >
            ✕
          </button>
        </div>

        <div className="space-y-4">
          <div className="flex gap-2">
            {(["TODO", "NOTE"] as ItemType[]).map((t) => (
              <button
                key={t}
                onClick={() => setType(t)}
                className={`flex-1 rounded-lg border px-3 py-1.5 text-sm font-medium transition-colors ${
                  type === t
                    ? "border-primary bg-primary/10 text-primary"
                    : "border-[var(--border)] text-[var(--text-secondary)]"
                }`}
              >
                {t === "TODO" ? "Todo" : "Note"}
              </button>
            ))}
          </div>

          <div>
            <label className="mb-1 block text-xs font-medium text-[var(--text-secondary)]">
              Title
            </label>
            <Input
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="e.g. Finish project report"
              autoFocus
            />
          </div>

          <div>
            <label className="mb-1 block text-xs font-medium text-[var(--text-secondary)]">
              Description (optional)
            </label>
            <textarea
              value={content}
              onChange={(e) => setContent(e.target.value)}
              placeholder="Add more details..."
              rows={3}
              className="w-full rounded-lg border border-[var(--border)] bg-[var(--bg-elevated)] px-3 py-2 text-sm text-[var(--text)] placeholder:text-[var(--text-secondary)] focus:outline-none focus:ring-2 focus:ring-primary"
            />
          </div>

          {type === "TODO" && (
            <div className="flex gap-3">
              <div className="flex-1">
                <label className="mb-1 block text-xs font-medium text-[var(--text-secondary)]">
                  Due Date
                </label>
                <Input
                  type="date"
                  value={dueDate}
                  onChange={(e) => setDueDate(e.target.value)}
                />
              </div>
              <div className="flex-1">
                <label className="mb-1 block text-xs font-medium text-[var(--text-secondary)]">
                  Priority
                </label>
                <select
                  value={priority}
                  onChange={(e) => setPriority(e.target.value as Priority)}
                  className="w-full rounded-lg border border-[var(--border)] bg-[var(--bg-elevated)] px-3 py-2 text-sm text-[var(--text)] focus:outline-none focus:ring-2 focus:ring-primary"
                >
                  <option value="LOW">Low</option>
                  <option value="MEDIUM">Medium</option>
                  <option value="HIGH">High</option>
                </select>
              </div>
            </div>
          )}

          {error && <p className="text-sm text-danger">{error}</p>}
        </div>

        <div className="mt-6 flex items-center justify-between gap-2">
          {onDelete ? (
            <Button variant="danger" onClick={onDelete} disabled={saving}>
              Delete
            </Button>
          ) : (
            <span />
          )}
          <div className="flex gap-2">
            <Button variant="secondary" onClick={onClose} disabled={saving}>
              Cancel
            </Button>
            <Button onClick={handleSave} disabled={saving}>
              {initial ? "Save Changes" : "Create Task"}
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
