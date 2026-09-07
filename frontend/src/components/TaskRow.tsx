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
      </div>
      {item.type === "TODO" && <PriorityBadge priority={item.priority} />}
      {item.due_date && (
        <span className="shrink-0 text-xs text-[var(--text-secondary)]">
          {formatDate(item.due_date)}
        </span>
      )}
    </div>
  );
}
