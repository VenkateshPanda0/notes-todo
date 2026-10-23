import { useCallback, useEffect, useState } from "react";
import { itemsApi } from "../api/client";
import { Button } from "../components/Button";
import { useItemsChangedRefresh } from "../hooks/useItemsChangedRefresh";
import type { Item } from "../types/item";

const RETENTION_DAYS = 30;

/** Whole days left before an item is deleted for good. */
function daysLeft(deletedAt: string | null | undefined): number {
  if (!deletedAt) return RETENTION_DAYS;
  const elapsed = (Date.now() - new Date(deletedAt).getTime()) / 86_400_000;
  return Math.max(0, Math.ceil(RETENTION_DAYS - elapsed));
}

export function TrashView() {
  const [items, setItems] = useState<Item[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [confirmEmpty, setConfirmEmpty] = useState(false);

  const load = useCallback(async () => {
    try {
      setItems(await itemsApi.listTrash());
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load the Trash.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);
  useItemsChangedRefresh(load);

  const run = async (action: () => Promise<unknown>) => {
    try {
      await action();
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "That didn't work.");
    }
    await load();
  };

  return (
    <div className="mx-auto max-w-3xl px-6 py-8">
      <div className="mb-2 flex items-center justify-between">
        <h1 className="text-2xl font-semibold text-[var(--text)]">Trash</h1>
        {items.length > 0 && !confirmEmpty ? (
          <Button variant="danger" onClick={() => setConfirmEmpty(true)}>
            Empty Trash
          </Button>
        ) : null}
      </div>
      <p className="mb-6 text-sm text-[var(--text-secondary)]">
        Deleted items stay here for {RETENTION_DAYS} days, then they are removed for good.
      </p>

      {confirmEmpty ? (
        <div
          role="alertdialog"
          aria-label="Empty the Trash"
          className="mb-6 flex items-center justify-between gap-4 rounded-lg border border-[var(--border)] bg-[var(--bg-elevated)] p-4"
        >
          <p className="text-sm text-[var(--text)]">
            Permanently delete {items.length} {items.length === 1 ? "item" : "items"}? This can't be undone.
          </p>
          <div className="flex gap-2">
            <Button variant="secondary" onClick={() => setConfirmEmpty(false)}>
              Cancel
            </Button>
            <Button
              variant="danger"
              onClick={async () => {
                setConfirmEmpty(false);
                await run(() => itemsApi.emptyTrash());
              }}
            >
              Delete all
            </Button>
          </div>
        </div>
      ) : null}

      {error ? (
        <p role="alert" className="mb-4 text-sm text-danger-ink">
          {error}
        </p>
      ) : null}

      {loading ? (
        <p className="text-sm text-[var(--text-secondary)]">Loading...</p>
      ) : items.length === 0 ? (
        <p className="rounded-lg border border-dashed border-[var(--border)] p-8 text-center text-sm text-[var(--text-secondary)]">
          The Trash is empty.
        </p>
      ) : (
        <ul className="flex flex-col gap-2">
          {items.map((item) => {
            const left = daysLeft(item.deleted_at);
            return (
              <li
                key={item.id}
                className="flex items-center justify-between gap-4 rounded-lg border border-[var(--border)] bg-[var(--bg-elevated)] px-4 py-3"
              >
                <div className="min-w-0">
                  <p className="truncate text-sm font-medium text-[var(--text)]">{item.title}</p>
                  <p className="text-xs text-[var(--text-secondary)]">
                    {item.type === "NOTE" ? "Note" : "Todo"} · {left} {left === 1 ? "day" : "days"} left
                  </p>
                </div>
                <div className="flex shrink-0 gap-2">
                  <Button variant="secondary" onClick={() => run(() => itemsApi.restore(item.id))}>
                    Restore
                  </Button>
                  <Button
                    variant="danger"
                    aria-label={`Delete "${item.title}" forever`}
                    onClick={() => run(() => itemsApi.purge(item.id))}
                  >
                    Delete forever
                  </Button>
                </div>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
