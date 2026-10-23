import { useEffect, useRef } from "react";
import { onItemsChanged } from "../lib/events";

/** Call `refresh` (debounced) whenever items change anywhere in the app, e.g. from the command palette.
 * The refresh should be quiet: update the data without flipping the page to a loading state. */
export function useItemsChangedRefresh(refresh: () => void): void {
  const latest = useRef(refresh);
  useEffect(() => {
    latest.current = refresh;
  });

  useEffect(() => {
    let timer: ReturnType<typeof setTimeout> | undefined;
    const stop = onItemsChanged(() => {
      clearTimeout(timer);
      timer = setTimeout(() => latest.current(), 200);
    });
    return () => {
      clearTimeout(timer);
      stop();
    };
  }, []);
}
