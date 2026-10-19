import { useEffect, useState } from "react";
import type { Ref } from "react";
import { itemsApi } from "../api/client";
import type { Item, ItemType, QuickAddPreview } from "../types/item";
import { PriorityBadge } from "./PriorityBadge";

interface QuickAddProps {
  defaultType: ItemType;
  onCreated: (item: Item) => void;
  inputRef?: Ref<HTMLInputElement>;
}

const HAS_TYPE_PREFIX = /^\s*(note|todo)\s*:/i;

function withDefaultType(text: string, defaultType: ItemType): string {
  if (defaultType === "NOTE" && !HAS_TYPE_PREFIX.test(text)) {
    return `note: ${text}`;
  }
  return text;
}

function formatDate(dateStr: string): string {
  // Parse as local midnight; `new Date("YYYY-MM-DD")` would be UTC and can shift the day.
  const [y, m, d] = dateStr.split("-").map(Number);
  return new Date(y, m - 1, d).toLocaleDateString(undefined, {
    weekday: "short",
    month: "short",
    day: "numeric",
  });
}

export function QuickAdd({ defaultType, onCreated, inputRef }: QuickAddProps) {
  const [text, setText] = useState("");
  const [preview, setPreview] = useState<QuickAddPreview | null>(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const trimmed = text.trim();

  // Debounced live preview of how the text will be interpreted.
  useEffect(() => {
    if (!trimmed) return;
    let cancelled = false;
    const timer = setTimeout(async () => {
      try {
        const result = await itemsApi.parse(withDefaultType(trimmed, defaultType));
        if (!cancelled) setPreview(result);
      } catch {
        if (!cancelled) setPreview(null);
      }
    }, 200);
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [trimmed, defaultType]);

  const submit = async () => {
    if (!trimmed || saving) return;
    setSaving(true);
    setError(null);
    try {
      const parsed = await itemsApi.parse(withDefaultType(trimmed, defaultType));
      const created = await itemsApi.create({
        title: parsed.title,
        type: parsed.type,
        priority: parsed.priority,
        due_date: parsed.due_date,
        tags: parsed.tags,
      });
      onCreated(created);
      setText("");
      setPreview(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not add item.");
    } finally {
      setSaving(false);
    }
  };

  const shown = trimmed ? preview : null;

  return (
    <div className="mb-4">
      <input
        ref={inputRef}
        value={text}
        disabled={saving}
        onChange={(e) => setText(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter") submit();
          if (e.key === "Escape") e.currentTarget.blur();
        }}
        placeholder={
          defaultType === "NOTE"
            ? 'Quick add a note…  (press "/" to focus)'
            : 'Quick add…  try "call dentist tomorrow !high #errands"  (press "/" to focus)'
        }
        aria-label="Quick add"
        className="w-full rounded-lg border border-[var(--border)] bg-[var(--bg-elevated)] px-3 py-2 text-sm text-[var(--text)] placeholder:text-[var(--text-secondary)] focus:outline-none focus:ring-2 focus:ring-primary"
      />

      {shown && (
        <div className="mt-2 flex flex-wrap items-center gap-2 text-xs text-[var(--text-secondary)]">
          <span>
            Adds {shown.type === "NOTE" ? "note" : "todo"}{" "}
            <strong className="text-[var(--text)]">{shown.title}</strong>
          </span>
          {shown.type === "TODO" && <PriorityBadge priority={shown.priority} />}
          {shown.due_date && (
            <span className="rounded-full bg-[var(--border)]/40 px-2.5 py-0.5 font-medium">
              Due {formatDate(shown.due_date)}
            </span>
          )}
          {shown.tags.map((tag) => (
            <span key={tag} className="rounded-full bg-primary/10 px-2.5 py-0.5 font-medium text-primary">
              #{tag}
            </span>
          ))}
          <span className="ml-auto">Enter to add</span>
        </div>
      )}

      {error && <p className="mt-2 text-xs text-danger">{error}</p>}
    </div>
  );
}
