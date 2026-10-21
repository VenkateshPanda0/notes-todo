import { useState } from "react";
import { authApi } from "../api/client";
import { useLock } from "../contexts/LockContext";
import { Button } from "./Button";
import { Input } from "./Input";

type Action = "enable" | "disable" | null;

/** Settings card section for encrypting the database file with the App Lock password. */
export function EncryptionSettings() {
  const { hasPassword, encrypted, encryptionAvailable, refreshStatus } = useLock();
  const [open, setOpen] = useState<Action>(null);
  const [password, setPassword] = useState("");
  const [understood, setUnderstood] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  if (!hasPassword) return null; // the App Lock password is the encryption key, so it comes first

  const reset = () => {
    setOpen(null);
    setPassword("");
    setUnderstood(false);
    setError(null);
  };

  const submit = async () => {
    if (!open) return;
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      if (open === "enable") {
        const result = await authApi.enableEncryption(password);
        setMessage(
          "Your database is now encrypted." +
            (result.removed_plain_backups > 0
              ? ` ${result.removed_plain_backups} older unencrypted backup${result.removed_plain_backups === 1 ? " was" : "s were"} securely deleted and replaced with an encrypted one.`
              : ""),
        );
      } else {
        await authApi.disableEncryption(password);
        setMessage("Encryption removed. Your database is a regular, unencrypted file again.");
      }
      reset();
      await refreshStatus();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="mt-6 border-t border-[var(--border)] pt-6">
      <h3 className="mb-1 text-sm font-semibold text-[var(--text)]">Database encryption</h3>

      {!encryptionAvailable ? (
        <p className="text-sm text-[var(--text-secondary)]">
          Encrypting the data file isn't available in this build of TaskFlow.
        </p>
      ) : (
        <>
          <p className="mb-3 text-sm text-[var(--text-secondary)]">
            {encrypted
              ? "Your data file is encrypted (AES-256) with your app password. It can't be read without it, even by other programs on this computer."
              : "The App Lock keeps people out of the app, but the data file itself is readable by anyone with access to your files. Encrypting it protects the file on disk, including backups."}
          </p>

          {!open && (
            <Button variant="secondary" onClick={() => setOpen(encrypted ? "disable" : "enable")}>
              {encrypted ? "Remove encryption…" : "Encrypt database…"}
            </Button>
          )}

          {open === "enable" && (
            <div className="space-y-3 rounded-lg border border-[var(--border)] p-4" role="group" aria-label="Encrypt database">
              <p className="rounded-lg bg-amber-50 p-3 text-sm text-[var(--text)] dark:bg-amber-950">
                <strong>If you forget your password, your notes cannot be recovered.</strong> There is no
                reset and no back door. Consider exporting a copy first (Backup &amp; export above).
              </p>
              <ul className="list-disc space-y-1 pl-5 text-xs text-[var(--text-secondary)]">
                <li>Your app password becomes the encryption key; changing it later re-encrypts the file.</li>
                <li>Older unencrypted backups are securely deleted and a fresh encrypted one is made.</li>
                <li>Exports (JSON, Markdown) are plain files by design: keep them somewhere safe.</li>
                <li>Don't close TaskFlow while it works; a copy of your data is kept until the result is verified.</li>
              </ul>
              <Input
                type="password"
                placeholder="Confirm your app password"
                aria-label="Confirm your app password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
              <label className="flex cursor-pointer items-start gap-2 text-sm text-[var(--text)]">
                <input
                  type="checkbox"
                  checked={understood}
                  onChange={(e) => setUnderstood(e.target.checked)}
                  className="mt-1"
                />
                <span>I understand that a forgotten password means permanently lost data.</span>
              </label>
              {error && <p className="text-sm text-danger-ink">{error}</p>}
              <div className="flex gap-2">
                <Button onClick={submit} disabled={busy || !understood || password.length < 4}>
                  {busy ? "Encrypting…" : "Encrypt now"}
                </Button>
                <Button variant="secondary" onClick={reset} disabled={busy}>
                  Cancel
                </Button>
              </div>
            </div>
          )}

          {open === "disable" && (
            <div className="space-y-3 rounded-lg border border-[var(--border)] p-4" role="group" aria-label="Remove encryption">
              <p className="text-sm text-[var(--text-secondary)]">
                Your data file will become a regular, readable file again. Existing encrypted backups stay
                encrypted.
              </p>
              <Input
                type="password"
                placeholder="Confirm your app password"
                aria-label="Confirm your app password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
              {error && <p className="text-sm text-danger-ink">{error}</p>}
              <div className="flex gap-2">
                <Button onClick={submit} disabled={busy || password.length < 4}>
                  {busy ? "Working…" : "Remove encryption"}
                </Button>
                <Button variant="secondary" onClick={reset} disabled={busy}>
                  Cancel
                </Button>
              </div>
            </div>
          )}
        </>
      )}

      {message && <p className="mt-3 text-sm text-success-ink">{message}</p>}
    </div>
  );
}
