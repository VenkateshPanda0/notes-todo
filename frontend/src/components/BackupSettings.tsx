import { useEffect, useRef, useState } from "react";
import { backupApi } from "../api/client";
import type { AutoBackupList } from "../types/item";
import { Button } from "./Button";

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

/** Settings card: export, import and automatic backups. */
export function BackupSettings() {
  const fileInput = useRef<HTMLInputElement>(null);
  const [mode, setMode] = useState<"merge" | "replace">("merge");
  const [busy, setBusy] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [auto, setAuto] = useState<AutoBackupList | null>(null);

  useEffect(() => {
    let cancelled = false;
    backupApi
      .auto()
      .then((list) => {
        if (!cancelled) setAuto(list);
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, []);

  const run = async (name: string, action: () => Promise<void>, done?: string) => {
    setBusy(name);
    setError(null);
    setMessage(null);
    try {
      await action();
      if (done) setMessage(done);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong.");
    } finally {
      setBusy(null);
    }
  };

  const onImport = async () => {
    const file = fileInput.current?.files?.[0];
    if (!file) {
      setError("Choose a file to import first.");
      return;
    }
    if (
      mode === "replace" &&
      !window.confirm(
        "Replace EVERYTHING in TaskFlow with the contents of this file?\n\n" +
          "A safety copy of your current data is saved automatically first.",
      )
    ) {
      return;
    }
    await run("import", async () => {
      const result = await backupApi.importFile(file, mode);
      setMessage(
        result.mode === "replace"
          ? `Replaced your data with ${result.imported} item${result.imported === 1 ? "" : "s"}.`
          : `Imported ${result.imported} item${result.imported === 1 ? "" : "s"}` +
              (result.skipped ? `, skipped ${result.skipped} that already existed.` : "."),
      );
      if (fileInput.current) fileInput.current.value = "";
      setAuto(await backupApi.auto());
    });
  };

  return (
    <section className="mb-8 rounded-xl border border-[var(--border)] bg-[var(--bg-elevated)] p-6">
      <h2 className="mb-1 text-sm font-semibold text-[var(--text)]">Backup &amp; export</h2>
      <p className="mb-4 text-sm text-[var(--text-secondary)]">
        Your data lives in one file on this computer. Keep copies somewhere safe, or move your notes
        to another app.
      </p>

      <div className="mb-5 flex flex-wrap gap-2">
        <Button variant="secondary" disabled={busy !== null} onClick={() => run("json", backupApi.exportJson)}>
          Export everything (JSON)
        </Button>
        <Button variant="secondary" disabled={busy !== null} onClick={() => run("md", backupApi.exportMarkdown)}>
          Export as Markdown (.zip)
        </Button>
        <Button variant="secondary" disabled={busy !== null} onClick={() => run("db", backupApi.downloadDatabase)}>
          Download database copy
        </Button>
      </div>

      <div className="rounded-lg border border-[var(--border)] p-4">
        <p className="mb-1 text-sm font-medium text-[var(--text)]">Import</p>
        <p className="mb-3 text-xs text-[var(--text-secondary)]">
          A TaskFlow JSON export, or a .zip of Markdown files (for example from Obsidian).
        </p>
        <input
          ref={fileInput}
          type="file"
          accept=".json,.zip,application/json,application/zip"
          aria-label="File to import"
          className="mb-3 block w-full text-sm text-[var(--text-secondary)]"
        />
        <div className="mb-3 space-y-1.5 text-sm text-[var(--text)]">
          <label className="flex cursor-pointer items-start gap-2">
            <input
              type="radio"
              name="import-mode"
              checked={mode === "merge"}
              onChange={() => setMode("merge")}
              className="mt-1 text-primary-ink focus:ring-primary"
            />
            <span>
              Merge <span className="text-[var(--text-secondary)]">(recommended): add what's missing, skip duplicates</span>
            </span>
          </label>
          <label className="flex cursor-pointer items-start gap-2">
            <input
              type="radio"
              name="import-mode"
              checked={mode === "replace"}
              onChange={() => setMode("replace")}
              className="mt-1 text-primary-ink focus:ring-primary"
            />
            <span>
              Replace everything{" "}
              <span className="text-[var(--text-secondary)]">(a safety copy is saved first)</span>
            </span>
          </label>
        </div>
        <Button disabled={busy !== null} onClick={onImport}>
          {busy === "import" ? "Importing…" : "Import"}
        </Button>
      </div>

      {error && <p className="mt-3 text-sm text-danger-ink">{error}</p>}
      {message && <p className="mt-3 text-sm text-success-ink">{message}</p>}

      {auto && (
        <div className="mt-5 border-t border-[var(--border)] pt-4">
          <p className="mb-1 text-sm font-medium text-[var(--text)]">Automatic backups</p>
          {auto.enabled ? (
            <>
              <p className="text-xs text-[var(--text-secondary)]">
                A snapshot is saved every day you use TaskFlow (the newest 7 are kept) in{" "}
                <code className="break-all">{auto.directory}</code>
              </p>
              <p className="mt-1 text-xs text-[var(--text-secondary)]">
                {auto.backups.length === 0
                  ? "No backups yet."
                  : `${auto.backups.length} saved · latest ${auto.backups[0].name} (${formatSize(auto.backups[0].size)})`}
              </p>
              <Button
                variant="secondary"
                className="mt-2"
                disabled={busy !== null}
                onClick={() =>
                  run(
                    "auto",
                    async () => setAuto(await backupApi.runAuto()),
                    "Backup saved.",
                  )
                }
              >
                Back up now
              </Button>
            </>
          ) : (
            <p className="text-xs text-[var(--text-secondary)]">
              Not available for the database this app is using.
            </p>
          )}
        </div>
      )}
    </section>
  );
}
