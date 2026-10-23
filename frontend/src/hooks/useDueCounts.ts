import { useEffect, useState } from "react";
import { itemsApi } from "../api/client";
import { countDue } from "../lib/dates";
import { onItemsChanged } from "../lib/events";

const REFRESH_EVERY_MS = 5 * 60 * 1000; // also catches the date rolling over while the app stays open

/** How many open todos are due today or overdue, kept fresh without any page having to report changes. */
export function useDueCounts(): { today: number; overdue: number } {
  const [counts, setCounts] = useState({ today: 0, overdue: 0 });

  useEffect(() => {
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout> | undefined;

    const refresh = () =>
      itemsApi
        .list({ type: "TODO", completed: false })
        .then((items) => {
          if (!cancelled) setCounts(countDue(items));
        })
        .catch(() => {});
    const refreshSoon = () => {
      clearTimeout(timer); // a burst of edits (an import, several toggles) costs one request
      timer = setTimeout(refresh, 150);
    };

    refresh();
    const stop = onItemsChanged(refreshSoon);
    window.addEventListener("focus", refreshSoon);
    const interval = setInterval(refresh, REFRESH_EVERY_MS);
    return () => {
      cancelled = true;
      clearTimeout(timer);
      stop();
      window.removeEventListener("focus", refreshSoon);
      clearInterval(interval);
    };
  }, []);

  return counts;
}
