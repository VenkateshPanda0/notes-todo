import { useEffect, useRef, useState } from "react";
import { onToast, type Toast } from "../lib/toast";

const VISIBLE_MS = 8000;

/** Shows the latest toast at the bottom of the screen; it dismisses itself after a few seconds. */
export function ToastHost() {
  const [toast, setToast] = useState<Toast | null>(null);
  const timer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);

  useEffect(() => {
    const stop = onToast((next) => {
      clearTimeout(timer.current);
      setToast(next);
      timer.current = setTimeout(() => setToast(null), VISIBLE_MS);
    });
    return () => {
      clearTimeout(timer.current);
      stop();
    };
  }, []);

  return (
    <div className="pointer-events-none fixed inset-x-0 bottom-4 z-[70] flex justify-center px-4">
      <div role="status" aria-live="polite">
        {toast ? (
          <div className="pointer-events-auto flex items-center gap-4 rounded-lg bg-[var(--text)] px-4 py-2.5 text-sm text-[var(--bg)] shadow-lg">
            <span>{toast.message}</span>
            {toast.actionLabel ? (
              <button
                type="button"
                className="font-semibold underline underline-offset-2 hover:no-underline"
                onClick={async () => {
                  clearTimeout(timer.current);
                  setToast(null);
                  await toast.onAction?.();
                }}
              >
                {toast.actionLabel}
              </button>
            ) : null}
            <button
              type="button"
              aria-label="Dismiss"
              className="opacity-70 hover:opacity-100"
              onClick={() => setToast(null)}
            >
              ×
            </button>
          </div>
        ) : null}
      </div>
    </div>
  );
}
