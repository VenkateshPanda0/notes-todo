import { NavLink } from "react-router-dom";
import { useAi } from "../contexts/ai-context";
import { useDueCounts } from "../hooks/useDueCounts";

const navItems = [
  { to: "/", label: "All Tasks", end: true },
  { to: "/today", label: "Today" },
  { to: "/upcoming", label: "Upcoming" },
  { to: "/completed", label: "Completed" },
  { to: "/notes", label: "Notes" },
  { to: "/calendar", label: "Calendar" },
  { to: "/graph", label: "Graph" },
  { to: "/trash", label: "Trash" },
];

function dueDescription(due: { today: number; overdue: number }): string {
  const parts: string[] = [];
  if (due.today > 0) parts.push(`${due.today} due today`);
  if (due.overdue > 0) parts.push(`${due.overdue} overdue`);
  return parts.join(", ");
}

export function Sidebar() {
  const { status } = useAi();
  const due = useDueCounts();
  // "Ask" only exists once local AI is switched on.
  const items = status?.enabled ? [...navItems, { to: "/ask", label: "Ask your notes", end: false }] : navItems;

  return (
    <aside className="flex w-56 shrink-0 flex-col border-r border-[var(--border)] bg-[var(--bg-elevated)] p-4">
      <div className="mb-6 flex items-center gap-2 px-2">
        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary text-white">
          <svg
            width="16"
            height="16"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="3"
          >
            <path d="M20 6L9 17l-5-5" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>
        <span className="font-semibold text-[var(--text)]">TaskFlow</span>
      </div>

      <nav aria-label="Main" className="flex flex-1 flex-col gap-1">
        {items.map((item) => {
          const badge = item.to === "/today" ? due.today + due.overdue : 0;
          return (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              aria-label={badge > 0 ? `${item.label}, ${dueDescription(due)}` : undefined}
              className={({ isActive }) =>
                `flex items-center justify-between rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
                  isActive
                    ? "bg-primary/10 text-primary-ink"
                    : "text-[var(--text-secondary)] hover:bg-[var(--border)]/40"
                }`
              }
            >
              {item.label}
              {badge > 0 && (
                <span
                  aria-hidden="true"
                  data-testid="today-badge"
                  className={`min-w-5 rounded-full px-1.5 py-0.5 text-center text-xs font-semibold ${
                    due.overdue > 0
                      ? "bg-red-50 text-danger-ink dark:bg-red-950"
                      : "bg-primary/10 text-primary-ink"
                  }`}
                >
                  {badge}
                </span>
              )}
            </NavLink>
          );
        })}
      </nav>

      <NavLink
        to="/settings"
        className={({ isActive }) =>
          `rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
            isActive
              ? "bg-primary/10 text-primary-ink"
              : "text-[var(--text-secondary)] hover:bg-[var(--border)]/40"
          }`
        }
      >
        Settings
      </NavLink>
    </aside>
  );
}
