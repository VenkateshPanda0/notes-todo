import type { Priority } from "../types/item";

const styles: Record<Priority, string> = {
  HIGH: "bg-red-50 text-danger dark:bg-red-950",
  MEDIUM: "bg-amber-50 text-warning dark:bg-amber-950",
  LOW: "bg-blue-50 text-primary dark:bg-blue-950",
};

const labels: Record<Priority, string> = {
  HIGH: "High",
  MEDIUM: "Medium",
  LOW: "Low",
};

export function PriorityBadge({ priority }: { priority: Priority }) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${styles[priority]}`}
    >
      {labels[priority]}
    </span>
  );
}
