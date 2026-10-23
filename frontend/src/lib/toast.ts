/** A tiny app-wide toast signal. Anything can call showToast(); <ToastHost /> renders it. */

export interface Toast {
  id: number;
  message: string;
  actionLabel?: string;
  onAction?: () => void | Promise<void>;
}

type Listener = (toast: Toast) => void;

const listeners = new Set<Listener>();
let nextId = 1;

export function showToast(toast: Omit<Toast, "id">): void {
  const full = { ...toast, id: nextId++ };
  listeners.forEach((listener) => listener(full));
}

/** Subscribe; returns the unsubscribe function. */
export function onToast(listener: Listener): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}
