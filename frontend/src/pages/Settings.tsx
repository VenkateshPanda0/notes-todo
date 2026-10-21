import { useState } from "react";
import { aiApi, authApi } from "../api/client";
import { BackupSettings } from "../components/BackupSettings";
import { EncryptionSettings } from "../components/EncryptionSettings";
import { Button } from "../components/Button";
import { Input } from "../components/Input";
import { useAi } from "../contexts/ai-context";
import { useLock } from "../contexts/LockContext";
import { useTheme } from "../contexts/ThemeContext";

export function Settings() {
  const { mode, setMode } = useTheme();
  const { hasPassword, refreshStatus, lockAgain } = useLock();
  const { status: ai, setStatus: setAiStatus, refresh: refreshAi } = useAi();
  const [aiError, setAiError] = useState<string | null>(null);
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

  const saveAi = async (payload: { enabled?: boolean; model?: string; embed_model?: string }) => {
    setAiError(null);
    // Optimistic: reflect the change immediately, then reconcile with the server's answer.
    if (ai) setAiStatus({ ...ai, ...payload });
    try {
      setAiStatus(await aiApi.updateSettings(payload));
    } catch (err) {
      setAiError(err instanceof Error ? err.message : "Could not save AI settings.");
      await refreshAi();
    }
  };

  const chatModels = (ai?.models ?? []).filter((m) => !/embed|minilm|bge-|e5-|gte-/i.test(m));
  const embedModels = (ai?.models ?? []).filter((m) => /embed|minilm|bge-|e5-|gte-/i.test(m));
  const selectClass =
    "w-full rounded-lg border border-[var(--border)] bg-[var(--bg-elevated)] px-3 py-2 text-sm text-[var(--text)] focus:outline-none focus:ring-2 focus:ring-primary";

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
                className="text-primary-ink focus:ring-primary"
              />
              <span className="capitalize">
                {option === "system" ? "System default" : `${option} mode`}
              </span>
            </label>
          ))}
        </div>
      </section>

      <BackupSettings />

      <section className="mb-8 rounded-xl border border-[var(--border)] bg-[var(--bg-elevated)] p-6">
        <h2 className="mb-1 text-sm font-semibold text-[var(--text)]">Local AI (beta)</h2>
        <p className="mb-4 text-sm text-[var(--text-secondary)]">
          Summaries, a daily plan and related-note suggestions, powered by{" "}
          <a className="text-primary-ink underline" href="https://ollama.com" target="_blank" rel="noreferrer">
            Ollama
          </a>{" "}
          running on this computer. Off by default; your notes are never sent to a cloud service.
        </p>

        <label className="mb-4 flex cursor-pointer items-center gap-2 text-sm text-[var(--text)]">
          <input
            type="checkbox"
            checked={ai?.enabled ?? false}
            disabled={!ai}
            onChange={(e) => saveAi({ enabled: e.target.checked })}
            className="text-primary-ink focus:ring-primary"
          />
          Enable local AI features
        </label>

        {ai && !ai.available && (
          <div className="mb-4 rounded-lg bg-amber-50 p-3 text-sm text-[var(--text)] dark:bg-amber-950">
            <p className="font-medium">Ollama was not detected at {ai.base_url}</p>
            <p className="mt-1 text-[var(--text-secondary)]">
              Install it from ollama.com, then run <code>ollama pull llama3.2</code> and{" "}
              <code>ollama pull nomic-embed-text</code>.
            </p>
            <Button variant="secondary" className="mt-2" onClick={refreshAi}>
              Check again
            </Button>
          </div>
        )}

        {ai && ai.available && (
          <div className="space-y-3">
            <p className="text-sm text-[var(--text-secondary)]">
              Connected to Ollama · {ai.models.length} model{ai.models.length === 1 ? "" : "s"} installed
            </p>
            {!ai.local && (
              <p className="rounded-lg bg-red-50 p-3 text-sm text-danger-ink dark:bg-red-950">
                Ollama at {ai.base_url} is not on this computer. With AI enabled, your notes would be
                sent to that server.
              </p>
            )}
            <div>
              <label className="mb-1 block text-xs font-medium text-[var(--text-secondary)]">
                Chat model (summaries and daily plan)
              </label>
              <select
                value={ai.model}
                onChange={(e) => saveAi({ model: e.target.value })}
                className={selectClass}
                aria-label="Chat model"
              >
                <option value="">Automatic (first installed)</option>
                {chatModels.map((m) => (
                  <option key={m} value={m}>
                    {m}
                  </option>
                ))}
              </select>
              {!ai.chat_model_ready && (
                <p className="mt-1 text-xs text-warning-ink">
                  No chat model found. Run <code>ollama pull llama3.2</code>.
                </p>
              )}
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-[var(--text-secondary)]">
                Embedding model (related notes)
              </label>
              <select
                value={ai.embed_model}
                onChange={(e) => saveAi({ embed_model: e.target.value })}
                className={selectClass}
                aria-label="Embedding model"
              >
                <option value="">Automatic (first installed)</option>
                {embedModels.map((m) => (
                  <option key={m} value={m}>
                    {m}
                  </option>
                ))}
              </select>
              {!ai.embed_model_ready && (
                <p className="mt-1 text-xs text-warning-ink">
                  No embedding model found. Run <code>ollama pull nomic-embed-text</code>.
                </p>
              )}
            </div>
          </div>
        )}
        {aiError && <p className="mt-3 text-sm text-danger-ink">{aiError}</p>}
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
          {error && <p className="text-sm text-danger-ink">{error}</p>}
          {message && <p className="text-sm text-success-ink">{message}</p>}
          <Button onClick={handleChangePassword}>
            {hasPassword ? "Change Password" : "Set Password"}
          </Button>
        </div>

        <EncryptionSettings />

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
