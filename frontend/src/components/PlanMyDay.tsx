import { useState } from "react";
import { aiApi } from "../api/client";
import { useAi } from "../contexts/ai-context";
import type { AIPlan, Item } from "../types/item";
import { Button } from "./Button";

/** "Plan my day": asks the local model for a short plan from overdue, due-soon and urgent todos. */
export function PlanMyDay({ onOpenItem }: { onOpenItem: (item: Item) => void }) {
  const { status } = useAi();
  const [busy, setBusy] = useState(false);
  const [plan, setPlan] = useState<AIPlan | null>(null);
  const [error, setError] = useState<string | null>(null);

  if (!status?.enabled || !status.chat_model_ready) return null;

  const run = async () => {
    setBusy(true);
    setError(null);
    try {
      setPlan(await aiApi.planDay());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not make a plan.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="mb-4">
      <Button variant="secondary" onClick={run} disabled={busy}>
        {busy ? "Planning…" : "✨ Plan my day"}
      </Button>
      {busy && (
        <span className="ml-3 text-xs text-[var(--text-secondary)]">
          Running on your computer, this can take a moment…
        </span>
      )}
      {error && <p className="mt-2 text-sm text-danger-ink">{error}</p>}

      {plan && (
        <div className="mt-3 rounded-xl border border-[var(--border)] bg-[var(--bg-elevated)] p-4" role="region" aria-label="Daily plan">
          <div className="mb-2 flex items-center justify-between">
            <p className="text-xs font-medium text-[var(--text-secondary)]">
              Today's plan{plan.model ? ` · ${plan.model}` : ""}
            </p>
            <button
              onClick={() => setPlan(null)}
              className="text-xs text-[var(--text-secondary)] hover:text-[var(--text)]"
            >
              Dismiss
            </button>
          </div>
          <p className="whitespace-pre-wrap text-sm text-[var(--text)]">{plan.plan}</p>
          {plan.items.length > 0 && (
            <div className="mt-3 flex flex-wrap gap-2">
              {plan.items.map((item) => (
                <button
                  key={item.id}
                  onClick={() => onOpenItem(item)}
                  className="rounded-full border border-[var(--border)] px-2.5 py-0.5 text-xs text-[var(--text)] hover:border-primary/50"
                >
                  {item.title}
                </button>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
