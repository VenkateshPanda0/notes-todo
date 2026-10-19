import { useCallback, useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";
import { aiApi } from "../api/client";
import type { AIStatus } from "../types/item";
import { AiContext } from "./ai-context";

export function AiProvider({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<AIStatus | null>(null);

  const refresh = useCallback(
    () =>
      aiApi
        .status()
        .then(setStatus)
        .catch(() => setStatus(null)),
    [],
  );

  useEffect(() => {
    refresh();
  }, [refresh]);

  const value = useMemo(() => ({ status, refresh, setStatus }), [status, refresh]);
  return <AiContext.Provider value={value}>{children}</AiContext.Provider>;
}
