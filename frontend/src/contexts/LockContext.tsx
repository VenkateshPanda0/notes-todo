import { createContext, useContext, useEffect, useState } from "react";
import type { ReactNode } from "react";
import { authApi, setUnauthorizedHandler } from "../api/client";

interface LockContextValue {
  loading: boolean;
  hasPassword: boolean;
  /** The database file is encrypted with the app password. */
  encrypted: boolean;
  /** This build can encrypt the database file. */
  encryptionAvailable: boolean;
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
  const [encrypted, setEncrypted] = useState(false);
  const [encryptionAvailable, setEncryptionAvailable] = useState(false);
  const [unlocked, setUnlocked] = useState(false);

  // `loading` is only true for the very first check. Re-checking later must not flip the whole app
  // back to "Loading…": that would unmount the page (and lose messages such as "Password updated.").
  const refreshStatus = async () => {
    try {
      const status = await authApi.status();
      setHasPassword(status.is_locked);
      setEncrypted(status.encrypted);
      setEncryptionAvailable(status.encryption_available);
      if (!status.is_locked) setUnlocked(true);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    refreshStatus();
  }, []);

  useEffect(() => {
    setUnauthorizedHandler(() => setUnlocked(false));
    return () => setUnauthorizedHandler(null);
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
    // Revoke the server-side session; lock the UI even if the request fails.
    authApi.lock().catch(() => {});
    setUnlocked(false);
  };

  return (
    <LockContext.Provider
      value={{
        loading,
        hasPassword,
        encrypted,
        encryptionAvailable,
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
