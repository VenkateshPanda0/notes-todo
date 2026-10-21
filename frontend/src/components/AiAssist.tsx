import { useState } from "react";
import { aiApi } from "../api/client";
import { useAi } from "../contexts/ai-context";
import type { AIRelated, AISummary, Item } from "../types/item";
import { Button } from "./Button";

interface AiAssistProps {
  item: Item;
  /** Add the summary to the note's text (the user still has to save). */
  onInsertSummary: (summary: string) => void;
  onOpenItem?: (item: Item) => void;
}

/** Summarize and "related items" actions for an existing note or todo, powered by local Ollama. */
export function AiAssist({ item, onInsertSummary, onOpenItem }: AiAssistProps) {
  const { status } = useAi();
  const [busy, setBusy] = useState<"summary" | "related" | null>(null);
  const [summary, setSummary] = useState<AISummary | null>(null);
  const [related, setRelated] = useState<AIRelated[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  if (!status?.enabled) return null;

  const run = async (kind: "summary" | "related") => {
    setBusy(kind);
    setError(null);
    try {
      if (kind === "summary") setSummary(await aiApi.summarize(item.id));
      else setRelated(await aiApi.related(item.id));
    } catch (err) {
      setError(err instanceof Error ? err.message : "The AI request failed.");
    } finally {
      setBusy(null);
    }
  };

  return (
    <div className="rounded-lg border border-[var(--border)] p-3">
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-xs font-medium text-[var(--text-secondary)]">Local AI</span>
        <Button
          variant="secondary"
          onClick={() => run("summary")}
          disabled={busy !== null || !status.chat_model_ready}
          title={status.chat_model_ready ? undefined : "No chat model installed in Ollama"}
        >
          {busy === "summary" ? "Summarizing…" : "✨ Summarize"}
        </Button>
        <Button
          variant="secondary"
          onClick={() => run("related")}
          disabled={busy !== null || !status.embed_model_ready}
          title={status.embed_model_ready ? undefined : "No embedding model installed in Ollama"}
        >
          {busy === "related" ? "Searching…" : "🔗 Find related"}
        </Button>
        {busy && (
          <span className="text-xs text-[var(--text-secondary)]">
            Running on your computer, this can take a moment…
          </span>
        )}
      </div>

      {error && <p className="mt-2 text-xs text-danger-ink">{error}</p>}

      {summary && (
        <div className="mt-3 rounded-lg bg-primary/5 p-3">
          <p className="mb-1 text-xs font-medium text-[var(--text-secondary)]">
            Summary · {summary.model}
          </p>
          <p className="whitespace-pre-wrap text-sm text-[var(--text)]">{summary.summary}</p>
          <div className="mt-2 flex gap-2">
            <Button
              variant="secondary"
              onClick={() => {
                onInsertSummary(summary.summary);
                setSummary(null);
              }}
            >
              Add to note
            </Button>
            <Button variant="secondary" onClick={() => setSummary(null)}>
              Dismiss
            </Button>
          </div>
        </div>
      )}

      {related && (
        <div className="mt-3">
          <p className="mb-1 text-xs font-medium text-[var(--text-secondary)]">
            {related.length === 0 ? "Nothing else to compare with yet." : "Possibly related"}
          </p>
          <div className="flex flex-wrap gap-2">
            {related.map(({ item: other, score }) => (
              <button
                key={other.id}
                type="button"
                onClick={() => onOpenItem?.(other)}
                className="rounded-full border border-[var(--border)] px-2.5 py-0.5 text-xs text-[var(--text)] hover:border-primary/50"
                title={`Similarity ${(score * 100).toFixed(0)}%`}
              >
                {other.type === "NOTE" ? "📝" : "✓"} {other.title}
                <span className="ml-1 opacity-60">{(score * 100).toFixed(0)}%</span>
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
