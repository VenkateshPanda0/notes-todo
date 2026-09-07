import { createContext, useContext, useEffect, useState } from "react";
import type { ReactNode } from "react";
import { authApi } from "../api/client";

interface LockContextValue {
  loading: boolean;
  hasPassword: boolean;
  unlocked: boolean;
  setupPassword: (password: string) => Promise<void>;
  skipSetup: () => void;
  unlock: (password: string) => Promise<void>;
  lockAgain: () => void;
  refreshStatus: () => Promise<void>;
}

const LockContext = createContext<LockContextValue | undefined>(undefined);

export function LockProvider({ children }: { children: ReactNode }) {
  const [loading, setLoading] = useState(true);
  const [hasPassword, setHasPassword] = useState(false);
  const [unlocked, setUnlocked] = useState(false);

  const refreshStatus = async () => {
    setLoading(true);
    try {
      const status = await authApi.status();
      setHasPassword(status.is_locked);
      if (!status.is_locked) setUnlocked(true);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    refreshStatus();
  }, []);

  const setupPassword = async (password: string) => {
    await authApi.setup(password);
    setHasPassword(true);
    setUnlocked(true);
  };

  const skipSetup = () => {
    setUnlocked(true);
  };

  const unlock = async (password: string) => {
    await authApi.unlock(password);
    setUnlocked(true);
  };

  const lockAgain = () => {
    setUnlocked(false);
  };

  return (
    <LockContext.Provider
      value={{
        loading,
        hasPassword,
        unlocked,
        setupPassword,
        skipSetup,
        unlock,
        lockAgain,
        refreshStatus,
      }}
    >
      {children}
    </LockContext.Provider>
  );
}

export function useLock(): LockContextValue {
  const ctx = useContext(LockContext);
  if (!ctx) throw new Error("useLock must be used within LockProvider");
  return ctx;
}
