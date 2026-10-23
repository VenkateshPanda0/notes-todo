import { itemsApi } from "../api/client";
import type { Item } from "../types/item";
import { showToast } from "./toast";

/** Move an item to the Trash and offer a one-click Undo. */
export async function removeWithUndo(item: Pick<Item, "id" | "title">): Promise<void> {
  await itemsApi.remove(item.id);
  showToast({
    message: `Moved "${item.title}" to Trash`,
    actionLabel: "Undo",
    onAction: async () => {
      try {
        await itemsApi.restore(item.id);
      } catch {
        showToast({ message: "Could not restore that item" });
      }
    },
  });
}
