import { useState } from "react";
import { authApi } from "../api/client";
import { Button } from "../components/Button";
import { Input } from "../components/Input";
import { useLock } from "../contexts/LockContext";
import { useTheme } from "../contexts/ThemeContext";

export function Settings() {
  const { mode, setMode } = useTheme();
  const { hasPassword, refreshStatus, lockAgain } = useLock();
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleChangePassword = async () => {
    setError(null);
    setMessage(null);
    try {
      if (!hasPassword) {
        await authApi.setup(newPassword);
      } else {
        await authApi.changePassword(currentPassword, newPassword);
      }
      setMessage("Password updated.");
      setCurrentPassword("");
      setNewPassword("");
      await refreshStatus();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong.");
    }
  };

  return (
    <div className="mx-auto max-w-2xl px-6 py-8">
      <h1 className="mb-6 text-2xl font-semibold text-[var(--text)]">
        Settings
      </h1>

      <section className="mb-8 rounded-xl border border-[var(--border)] bg-[var(--bg-elevated)] p-6">
        <h2 className="mb-4 text-sm font-semibold text-[var(--text)]">
          Appearance
        </h2>
        <div className="space-y-2">
          {(["light", "dark", "system"] as const).map((option) => (
            <label
              key={option}
              className="flex cursor-pointer items-center gap-2 text-sm text-[var(--text)]"
            >
              <input
                type="radio"
                name="theme"
                checked={mode === option}
                onChange={() => setMode(option)}
                className="text-primary focus:ring-primary"
              />
              <span className="capitalize">
                {option === "system" ? "System default" : `${option} mode`}
              </span>
            </label>
          ))}
        </div>
      </section>

      <section className="rounded-xl border border-[var(--border)] bg-[var(--bg-elevated)] p-6">
        <h2 className="mb-4 text-sm font-semibold text-[var(--text)]">
          App Lock
        </h2>
        <p className="mb-4 text-sm text-[var(--text-secondary)]">
          {hasPassword
            ? "Change the password that locks TaskFlow on launch."
            : "No password is currently set. Add one to lock TaskFlow on launch."}
        </p>
        <div className="space-y-3">
          {hasPassword && (
            <Input
              type="password"
              placeholder="Current password"
              value={currentPassword}
              onChange={(e) => setCurrentPassword(e.target.value)}
            />
          )}
          <Input
            type="password"
            placeholder="New password"
            value={newPassword}
            onChange={(e) => setNewPassword(e.target.value)}
          />
          {error && <p className="text-sm text-danger">{error}</p>}
          {message && <p className="text-sm text-success">{message}</p>}
          <Button onClick={handleChangePassword}>
            {hasPassword ? "Change Password" : "Set Password"}
          </Button>
        </div>

        {hasPassword && (
          <div className="mt-6 border-t border-[var(--border)] pt-6">
            <Button variant="danger" onClick={lockAgain}>
              Lock now
            </Button>
          </div>
        )}
      </section>
    </div>
  );
}
