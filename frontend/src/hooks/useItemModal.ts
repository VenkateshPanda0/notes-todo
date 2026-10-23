import { useCallback, useMemo, useState } from "react";
import { itemsApi } from "../api/client";
import { normalizeTitle } from "../lib/markdown";
import { removeWithUndo } from "../lib/trash";
import type { Item, ItemType, Priority } from "../types/item";

interface SavePayload {
  title: string;
  content: string;
  type: ItemType;
  priority: Priority;
  due_date: string | null;
  tags: string[];
}

/**
 * State and handlers for TaskModal on pages that open existing items (not create new ones).
 * Spread `modalProps` onto <TaskModal />.
 */
export function useItemModal(options: { titles?: string[]; onChanged?: () => void | Promise<void> } = {}) {
  const { titles, onChanged } = options;
  const [open, setOpen] = useState(false);
  const [item, setItem] = useState<Item | null>(null);

  const openItem = useCallback((next: Item) => {
    setItem(next);
    setOpen(true);
  }, []);

  const knownTitles = useMemo(
    () => new Set((titles ?? []).map(normalizeTitle)),
    [titles],
  );

  const modalProps = {
    open,
    initial: item,
    knownTitles,
    onClose: () => setOpen(false),
    onOpenItem: (next: Item) => setItem(next),
    onSave: async (payload: SavePayload) => {
      if (!item) return;
      await itemsApi.update(item.id, payload);
      if (item.type !== payload.type) await itemsApi.convert(item.id);
      await onChanged?.();
    },
    onDelete: item
      ? async () => {
          await removeWithUndo(item);
          setOpen(false);
          await onChanged?.();
        }
      : undefined,
    // Follow a [[link]]: open the item with that title, or create a note for it.
    onOpenLink: async (title: string) => {
      const wanted = normalizeTitle(title);
      const all = await itemsApi.list();
      const found =
        all.find((i) => normalizeTitle(i.title) === wanted) ??
        (await itemsApi.create({ title: title.trim(), type: "NOTE" }));
      setItem(found);
      await onChanged?.();
    },
  };

  return { modalProps, openItem };
}
