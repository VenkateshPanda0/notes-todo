import { useState } from "react";
import { Button } from "../components/Button";
import { Input } from "../components/Input";
import { useLock } from "../contexts/LockContext";

export function LockScreen() {
  const { hasPassword, setupPassword, skipSetup, unlock } = useLock();
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const isFirstRun = !hasPassword;

  const handleSubmit = async () => {
    setError(null);
    if (isFirstRun) {
      if (password.length < 4) {
        setError("Password must be at least 4 characters.");
        return;
      }
      if (password !== confirmPassword) {
        setError("Passwords do not match.");
        return;
      }
      setSubmitting(true);
      try {
        await setupPassword(password);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Something went wrong.");
      } finally {
        setSubmitting(false);
      }
    } else {
      setSubmitting(true);
      try {
        await unlock(password);
      } catch {
        setError("Incorrect password.");
      } finally {
        setSubmitting(false);
      }
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-[var(--bg)] px-4">
      <div className="w-full max-w-sm rounded-xl border border-[var(--border)] bg-[var(--bg-elevated)] p-8 shadow-sm">
        <div className="mb-6 flex items-center gap-2">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary text-white">
            <svg
              width="20"
              height="20"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="3"
            >
              <path
                d="M20 6L9 17l-5-5"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          </div>
          <div>
            <h1 className="text-lg font-semibold text-[var(--text)]">
              TaskFlow
            </h1>
            <p className="text-xs text-[var(--text-secondary)]">
              Organize today. Do more tomorrow.
            </p>
          </div>
        </div>

        <h2 className="mb-1 text-base font-semibold text-[var(--text)]">
          {isFirstRun ? "Set an app password" : "Welcome back"}
        </h2>
        <p className="mb-5 text-sm text-[var(--text-secondary)]">
          {isFirstRun
            ? "Optional — lock TaskFlow with a password only you know."
            : "Enter your password to continue."}
        </p>

        <div className="space-y-3">
          <Input
            type="password"
            placeholder="Password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleSubmit()}
          />
          {isFirstRun && (
            <Input
              type="password"
              placeholder="Confirm password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleSubmit()}
            />
          )}
          {error && <p className="text-sm text-danger">{error}</p>}

          <Button
            onClick={handleSubmit}
            disabled={submitting}
            className="w-full"
          >
            {isFirstRun ? "Set Password" : "Sign In"}
          </Button>

          {isFirstRun && (
            <button
              onClick={skipSetup}
              className="w-full text-center text-sm text-[var(--text-secondary)] hover:text-[var(--text)]"
            >
              Skip for now
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
