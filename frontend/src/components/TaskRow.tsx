import type { Item } from "../types/item";
import { PriorityBadge } from "./PriorityBadge";

interface TaskRowProps {
  item: Item;
  onToggleComplete: (item: Item) => void;
  onClick: (item: Item) => void;
}

function formatDate(dateStr: string | null): string | null {
  if (!dateStr) return null;
  const date = new Date(dateStr + "T00:00:00");
  return date.toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

// First non-empty line of a note, with the most common Markdown markers removed.
function snippet(content: string): string {
  const line = content.split("\n").find((l) => l.trim()) ?? "";
  return line.replace(/^[#>*\-\s]+/, "").replace(/[*_`]/g, "").trim();
}

export function TaskRow({ item, onToggleComplete, onClick }: TaskRowProps) {
  return (
    <div
      className="flex cursor-pointer items-center gap-3 rounded-lg border border-[var(--border)] bg-[var(--bg-elevated)] px-4 py-3 transition-colors hover:border-primary/40"
      onClick={() => onClick(item)}
    >
      <input
        type="checkbox"
        checked={item.completed}
        onClick={(e) => e.stopPropagation()}
        onChange={() => onToggleComplete(item)}
        className="h-4 w-4 shrink-0 cursor-pointer rounded border-[var(--border)] text-primary focus:ring-primary"
      />
      <div className="min-w-0 flex-1">
        <p
          className={`truncate text-sm font-medium ${
            item.completed
              ? "text-[var(--text-secondary)] line-through"
              : "text-[var(--text)]"
          }`}
        >
          {item.title}
        </p>
        {item.type === "NOTE" && snippet(item.content) && (
          <p className="mt-0.5 truncate text-xs text-[var(--text-secondary)]">
            {snippet(item.content)}
          </p>
        )}
      </div>
      {item.tags.length > 0 && (
        <div className="hidden shrink-0 gap-1 sm:flex">
          {item.tags.slice(0, 3).map((tag) => (
            <span
              key={tag}
              className="rounded-full bg-primary/10 px-2 py-0.5 text-xs font-medium text-primary"
            >
              #{tag}
            </span>
          ))}
          {item.tags.length > 3 && (
            <span className="text-xs text-[var(--text-secondary)]">+{item.tags.length - 3}</span>
          )}
        </div>
      )}
      {item.type === "TODO" && <PriorityBadge priority={item.priority} />}
      {item.due_date && (
        <span className="shrink-0 text-xs text-[var(--text-secondary)]">
          {formatDate(item.due_date)}
        </span>
      )}
    </div>
  );
}
