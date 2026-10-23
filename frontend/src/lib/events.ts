/** A tiny app-wide signal: "items were created, changed or deleted". The API client fires it after
 * every successful write, so anything that summarises items (the sidebar badge) refreshes by itself. */

const ITEMS_CHANGED = "taskflow:items-changed";

export function notifyItemsChanged(): void {
  window.dispatchEvent(new Event(ITEMS_CHANGED));
}

/** Subscribe; returns the unsubscribe function. */
export function onItemsChanged(callback: () => void): () => void {
  window.addEventListener(ITEMS_CHANGED, callback);
  return () => window.removeEventListener(ITEMS_CHANGED, callback);
}
