import { NavLink } from "react-router-dom";

const navItems = [
  { to: "/", label: "All Tasks", end: true },
  { to: "/today", label: "Today" },
  { to: "/upcoming", label: "Upcoming" },
  { to: "/completed", label: "Completed" },
  { to: "/notes", label: "Notes" },
  { to: "/calendar", label: "Calendar" },
];

export function Sidebar() {
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

      <nav className="flex flex-1 flex-col gap-1">
        {navItems.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.end}
            className={({ isActive }) =>
              `rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
                isActive
                  ? "bg-primary/10 text-primary"
                  : "text-[var(--text-secondary)] hover:bg-[var(--border)]/40"
              }`
            }
          >
            {item.label}
          </NavLink>
        ))}
      </nav>

      <NavLink
        to="/settings"
        className={({ isActive }) =>
          `rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
            isActive
              ? "bg-primary/10 text-primary"
              : "text-[var(--text-secondary)] hover:bg-[var(--border)]/40"
          }`
        }
      >
        Settings
      </NavLink>
    </aside>
  );
}
