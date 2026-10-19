import { useEffect, useState } from "react";
import { itemsApi } from "../api/client";
import type { Item, ItemType, Priority } from "../types/item";
import { Button } from "./Button";
import { Input } from "./Input";
import { Markdown } from "./Markdown";

interface TaskModalProps {
  open: boolean;
  initial?: Item | null;
  defaultType?: ItemType;
  /** Normalized titles of existing items, used to style [[links]] that point nowhere. */
  knownTitles?: ReadonlySet<string>;
  onClose: () => void;
  onSave: (data: {
    title: string;
    content: string;
    type: ItemType;
    priority: Priority;
    due_date: string | null;
    tags: string[];
  }) => Promise<void>;
  onDelete?: () => Promise<void>;
  /** Open the item a [[link]] points to (creating it if needed). */
  onOpenLink?: (title: string) => void;
  onOpenItem?: (item: Item) => void;
}

const NO_TITLES: ReadonlySet<string> = new Set();

function parseTags(text: string): string[] {
  return text
    .split(/[\s,]+/)
    .map((t) => t.replace(/^#/, "").trim())
    .filter(Boolean);
}

export function TaskModal({
  open,
  initial,
  defaultType = "TODO",
  knownTitles = NO_TITLES,
  onClose,
  onSave,
  onDelete,
  onOpenLink,
  onOpenItem,
}: TaskModalProps) {
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const [type, setType] = useState<ItemType>("TODO");
  const [priority, setPriority] = useState<Priority>("MEDIUM");
  const [dueDate, setDueDate] = useState("");
  const [tagsText, setTagsText] = useState("");
  const [preview, setPreview] = useState(false);
  const [backlinks, setBacklinks] = useState<Item[]>([]);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (open) {
      setTagsText((initial?.tags ?? []).map((t) => `#${t}`).join(" "));
      setPreview(false);
      setBacklinks([]);
      setTitle(initial?.title ?? "");
      setContent(initial?.content ?? "");
      setType(initial?.type ?? defaultType);
      setPriority(initial?.priority ?? "MEDIUM");
      setDueDate(initial?.due_date ?? "");
      setError(null);
    }
  }, [open, initial, defaultType]);

  // Items that link to this one with [[Title]].
  useEffect(() => {
    if (!open || !initial) return;
    let cancelled = false;
    itemsApi
      .backlinks(initial.id)
      .then((items) => {
        if (!cancelled) setBacklinks(items);
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, [open, initial]);

  useEffect(() => {
    if (!open) return;
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [open, onClose]);

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
        tags: parseTags(tagsText),
      });
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong.");
    } finally {
      setSaving(false);
    }
  };

  const isDirty =
    title !== (initial?.title ?? "") ||
    content !== (initial?.content ?? "") ||
    tagsText.trim() !== (initial?.tags ?? []).map((t) => `#${t}`).join(" ");

  // Leaving for another item discards unsaved edits, so confirm first.
  const confirmLeave = () =>
    !isDirty || window.confirm("You have unsaved changes. Discard them and continue?");

  const isNote = type === "NOTE";

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <div
        className={`max-h-[92vh] w-full overflow-y-auto rounded-xl ${isNote ? "max-w-2xl" : "max-w-md"} border border-[var(--border)] bg-[var(--bg-elevated)] p-6 shadow-xl`}
      >
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-[var(--text)]">
            {initial ? (isNote ? "Edit Note" : "Edit Task") : isNote ? "Add Note" : "Add Task"}
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
            <div className="mb-1 flex items-center justify-between">
              <label className="block text-xs font-medium text-[var(--text-secondary)]">
                {isNote ? "Note" : "Description (optional)"} · Markdown supported
              </label>
              {content.trim() && (
                <div className="flex gap-1 text-xs">
                  {[false, true].map((showPreview) => (
                    <button
                      key={String(showPreview)}
                      type="button"
                      onClick={() => setPreview(showPreview)}
                      className={`rounded-md px-2 py-0.5 font-medium ${
                        preview === showPreview
                          ? "bg-primary/10 text-primary"
                          : "text-[var(--text-secondary)]"
                      }`}
                    >
                      {showPreview ? "Preview" : "Write"}
                    </button>
                  ))}
                </div>
              )}
            </div>
            {preview && content.trim() ? (
              <div className="min-h-24 rounded-lg border border-[var(--border)] px-3 py-2">
                <Markdown
                  source={content}
                  knownTitles={knownTitles}
                  onWikiLink={(t) => onOpenLink && confirmLeave() && onOpenLink(t)}
                />
              </div>
            ) : (
              <textarea
                value={content}
                onChange={(e) => setContent(e.target.value)}
                placeholder={
                  isNote
                    ? "Write in Markdown. Link to other notes or todos with [[Title]]."
                    : "Add more details..."
                }
                rows={isNote ? 12 : 3}
                className="w-full rounded-lg border border-[var(--border)] bg-[var(--bg-elevated)] px-3 py-2 font-[inherit] text-sm text-[var(--text)] placeholder:text-[var(--text-secondary)] focus:outline-none focus:ring-2 focus:ring-primary"
              />
            )}
          </div>

          <div>
            <label className="mb-1 block text-xs font-medium text-[var(--text-secondary)]">
              Tags
            </label>
            <Input
              value={tagsText}
              onChange={(e) => setTagsText(e.target.value)}
              placeholder="#work #ideas (separate with spaces or commas)"
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

          {initial && onOpenItem && backlinks.length > 0 && (
            <div>
              <p className="mb-1 text-xs font-medium text-[var(--text-secondary)]">
                Linked from ({backlinks.length})
              </p>
              <div className="flex flex-wrap gap-2">
                {backlinks.map((b) => (
                  <button
                    key={b.id}
                    type="button"
                    onClick={() => confirmLeave() && onOpenItem(b)}
                    className="rounded-full border border-[var(--border)] px-2.5 py-0.5 text-xs text-[var(--text)] hover:border-primary/50"
                  >
                    {b.type === "NOTE" ? "📝" : "✓"} {b.title}
                  </button>
                ))}
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
