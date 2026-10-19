import { createContext, useContext } from "react";
import type { AIStatus } from "../types/item";

export interface AiContextValue {
  /** null until the first check finishes, or if the check failed. */
  status: AIStatus | null;
  refresh: () => Promise<void>;
  /** Replace the cached status (e.g. with the response from saving settings). */
  setStatus: (status: AIStatus) => void;
}

export const AiContext = createContext<AiContextValue | undefined>(undefined);

export function useAi(): AiContextValue {
  const ctx = useContext(AiContext);
  if (!ctx) throw new Error("useAi must be used within AiProvider");
  return ctx;
}
