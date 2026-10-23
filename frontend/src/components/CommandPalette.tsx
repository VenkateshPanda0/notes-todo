import { useEffect, useId, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { itemsApi } from "../api/client";
import { useAi } from "../contexts/ai-context";
import { useItemModal } from "../hooks/useItemModal";
import { describeParsed } from "../lib/describe";
import type { Item, QuickAddPreview } from "../types/item";
import { TaskModal } from "./TaskModal";

interface Command {
  id: string;
  label: string;
  hint?: string;
  keywords: string;
  run: "navigate" | "help";
  path?: string;
}

const COMMANDS: Command[] = [
  { id: "go-all", label: "Go to All Tasks", keywords: "todos list home", run: "navigate", path: "/" },
  { id: "go-today", label: "Go to Today", keywords: "due overdue", run: "navigate", path: "/today" },
  { id: "go-upcoming", label: "Go to Upcoming", keywords: "future soon", run: "navigate", path: "/upcoming" },
  { id: "go-completed", label: "Go to Completed", keywords: "done finished", run: "navigate", path: "/completed" },
  { id: "go-notes", label: "Go to Notes", keywords: "markdown writing", run: "navigate", path: "/notes" },
  { id: "go-calendar", label: "Go to Calendar", keywords: "month dates", run: "navigate", path: "/calendar" },
  { id: "go-graph", label: "Go to Graph", keywords: "links map network", run: "navigate", path: "/graph" },
  { id: "go-trash", label: "Go to Trash", keywords: "deleted restore recover bin", run: "navigate", path: "/trash" },
  { id: "go-settings", label: "Go to Settings", keywords: "backup encryption password theme ai", run: "navigate", path: "/settings" },
  { id: "help", label: "Keyboard shortcuts", keywords: "help keys hotkeys", run: "help" },
];

const ASK: Command = {
  id: "go-ask",
  label: "Go to Ask your notes",
  keywords: "ai question chat",
  run: "navigate",
  path: "/ask",
};

const SHORTCUTS: [string, string][] = [
  ["Ctrl / ⌘ + K", "Open this palette from anywhere"],
  ["/", "Focus Quick Add on a task list"],
  ["n", "Open the new task form"],
  ["Enter", "Add the Quick Add text, or choose a palette result"],
  ["↑ ↓", "Move through palette results"],
  ["Esc", "Close a dialog or this palette"],
  ["Tab", "Move between fields; dialogs keep focus inside"],
];

type Row =
  | { kind: "capture"; id: string; text: string }
  | { kind: "command"; id: string; command: Command }
  | { kind: "item"; id: string; item: Item };

/** Ctrl/⌘+K: jump anywhere, find any note or todo, or capture something in one line. */
export function CommandPalette() {
  const navigate = useNavigate();
  const { status } = useAi();
  const uid = useId();
  const inputRef = useRef<HTMLInputElement>(null);
  const opener = useRef<HTMLElement | null>(null);

  const [open, setOpen] = useState(false);
  const [help, setHelp] = useState(false);
  const [query, setQuery] = useState("");
  const [active, setActive] = useState(0);
  const [items, setItems] = useState<Item[]>([]);
  const [preview, setPreview] = useState<{ text: string; value: QuickAddPreview } | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [announcement, setAnnouncement] = useState("");

  const loadItems = () =>
    itemsApi
      .list()
      .then(setItems)
      .catch(() => {});
  const { modalProps, openItem } = useItemModal({
    titles: items.map((i) => i.title),
    onChanged: loadItems,
  });

  const close = () => {
    setOpen(false);
    setHelp(false);
    setQuery("");
    setActive(0);
    setError(null);
    setPreview(null);
    opener.current?.focus();
  };

  // Ctrl/⌘+K toggles from anywhere, even while typing in a field.
  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        if (open) {
          close();
        } else {
          opener.current = document.activeElement instanceof HTMLElement ? document.activeElement : null;
          setOpen(true);
          loadItems();
        }
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [open]);

  useEffect(() => {
    if (open) inputRef.current?.focus();
  }, [open, help]);

  const text = query.trim();

  // Live preview of how the capture line will be understood (debounced).
  useEffect(() => {
    if (!open || !text) return;
    let cancelled = false;
    const timer = setTimeout(async () => {
      try {
        const value = await itemsApi.parse(text);
        if (!cancelled) setPreview({ text, value });
      } catch {
        if (!cancelled) setPreview(null);
      }
    }, 200);
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [open, text]);

  const rows = useMemo<Row[]>(() => {
    const q = text.toLowerCase();
    const commands = (status?.enabled ? [...COMMANDS.slice(0, -1), ASK, COMMANDS[COMMANDS.length - 1]] : COMMANDS).filter(
      (c) => !q || c.label.toLowerCase().includes(q) || c.keywords.includes(q),
    );
    const matches = q
      ? items.filter((i) => i.title.toLowerCase().includes(q) || i.content.toLowerCase().includes(q))
      : [...items].sort((a, b) => b.updated_at.localeCompare(a.updated_at)).slice(0, 5);
    const result: Row[] = [];
    if (text) result.push({ kind: "capture", id: "capture", text });
    for (const command of commands) result.push({ kind: "command", id: command.id, command });
    for (const item of matches.slice(0, 8)) result.push({ kind: "item", id: `item-${item.id}`, item });
    return result;
  }, [items, text, status?.enabled]);

  const safeActive = Math.min(active, Math.max(rows.length - 1, 0));

  const capture = async (line: string) => {
    setBusy(true);
    setError(null);
    try {
      const parsed = await itemsApi.parse(line);
      await itemsApi.create({
        title: parsed.title,
        type: parsed.type,
        priority: parsed.priority,
        due_date: parsed.due_date,
        recurrence: parsed.recurrence,
        tags: parsed.tags,
      });
      setAnnouncement(`Added ${parsed.type === "NOTE" ? "note" : "todo"}: ${parsed.title}`);
      close();
      loadItems();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not add that.");
    } finally {
      setBusy(false);
    }
  };

  const choose = (row: Row | undefined) => {
    if (!row || busy) return;
    if (row.kind === "capture") {
      void capture(row.text);
    } else if (row.kind === "command") {
      if (row.command.run === "help") {
        setHelp(true);
        setQuery("");
      } else {
        close();
        navigate(row.command.path!);
      }
    } else {
      close();
      openItem(row.item);
    }
  };

  const onInputKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Escape") {
      e.preventDefault();
      if (help) setHelp(false);
      else close();
    } else if (e.key === "ArrowDown") {
      e.preventDefault();
      setActive((safeActive + 1) % Math.max(rows.length, 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setActive((safeActive - 1 + rows.length) % Math.max(rows.length, 1));
    } else if (e.key === "Enter" && !help) {
      e.preventDefault();
      choose(rows[safeActive]);
    } else if (e.key === "Tab") {
      e.preventDefault(); // keep focus in the palette: it is a single-input dialog
    }
  };

  const optionId = (row: Row) => `${uid}-${row.id}`;
  const captureHint =
    preview && preview.text === text ? describeParsed(preview.value) : "Parsing…";

  return (
    <>
      <div role="status" aria-live="polite" className="sr-only">
        {announcement}
      </div>

      {open && (
        <div
          className="fixed inset-0 z-[55] flex items-start justify-center bg-black/40 p-4 pt-[12vh]"
          onMouseDown={(e) => e.target === e.currentTarget && close()}
        >
          <div
            role="dialog"
            aria-modal="true"
            aria-label="Command palette"
            className="w-full max-w-xl overflow-hidden rounded-xl border border-[var(--border)] bg-[var(--bg-elevated)] shadow-2xl"
          >
            <input
              ref={inputRef}
              role="combobox"
              aria-expanded={!help}
              aria-controls={`${uid}-list`}
              aria-activedescendant={!help && rows[safeActive] ? optionId(rows[safeActive]) : undefined}
              aria-autocomplete="list"
              aria-label="Search, jump, or add"
              value={query}
              onChange={(e) => {
                setQuery(e.target.value);
                setActive(0);
                setHelp(false);
              }}
              onKeyDown={onInputKeyDown}
              placeholder="Search notes, jump to a page, or type a task to add…"
              className="w-full border-b border-[var(--border)] bg-transparent px-4 py-3 text-sm text-[var(--text)] placeholder:text-[var(--text-secondary)] focus:outline-none"
            />

            {help ? (
              <div className="p-4">
                <p className="mb-3 text-xs font-semibold uppercase tracking-wide text-[var(--text-secondary)]">
                  Keyboard shortcuts
                </p>
                <dl className="space-y-2">
                  {SHORTCUTS.map(([keys, what]) => (
                    <div key={keys} className="flex items-baseline justify-between gap-4 text-sm">
                      <dt>
                        <kbd className="rounded border border-[var(--border)] bg-[var(--bg)] px-1.5 py-0.5 font-mono text-xs text-[var(--text)]">
                          {keys}
                        </kbd>
                      </dt>
                      <dd className="text-right text-[var(--text-secondary)]">{what}</dd>
                    </div>
                  ))}
                </dl>
                <p className="mt-4 text-xs text-[var(--text-secondary)]">Press Esc to go back.</p>
              </div>
            ) : (
              <ul id={`${uid}-list`} role="listbox" aria-label="Results" className="max-h-80 overflow-y-auto py-1">
                {rows.length === 0 && (
                  <li className="px-4 py-6 text-center text-sm text-[var(--text-secondary)]">Nothing matches.</li>
                )}
                {rows.map((row, index) => (
                  <li
                    key={row.id}
                    id={optionId(row)}
                    role="option"
                    aria-selected={index === safeActive}
                    onMouseMove={() => setActive(index)}
                    onClick={() => choose(row)}
                    className={`flex cursor-pointer items-center justify-between gap-3 px-4 py-2 text-sm ${
                      index === safeActive ? "bg-primary/10 text-primary-ink" : "text-[var(--text)]"
                    }`}
                  >
                    {row.kind === "capture" && (
                      <>
                        <span className="truncate">
                          <strong>Add</strong> “{row.text}”
                        </span>
                        <span className="shrink-0 text-xs text-[var(--text-secondary)]">{captureHint}</span>
                      </>
                    )}
                    {row.kind === "command" && (
                      <>
                        <span>{row.command.label}</span>
                        <span className="text-xs text-[var(--text-secondary)]">
                          {row.command.run === "navigate" ? "Go" : "Help"}
                        </span>
                      </>
                    )}
                    {row.kind === "item" && (
                      <>
                        <span className="truncate">
                          {row.item.type === "NOTE" ? "📝" : "✓"} {row.item.title}
                        </span>
                        <span className="shrink-0 text-xs text-[var(--text-secondary)]">
                          {row.item.type === "NOTE" ? "Note" : row.item.completed ? "Done" : "Todo"}
                        </span>
                      </>
                    )}
                  </li>
                ))}
              </ul>
            )}

            {error && <p className="border-t border-[var(--border)] px-4 py-2 text-sm text-danger-ink">{error}</p>}
            <p className="border-t border-[var(--border)] px-4 py-2 text-xs text-[var(--text-secondary)]">
              ↑↓ to move · Enter to choose · Esc to close
            </p>
          </div>
        </div>
      )}

      <TaskModal {...modalProps} />
    </>
  );
}
