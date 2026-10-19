import { useEffect, useMemo, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { aiApi, itemsApi } from "../api/client";
import { Button } from "../components/Button";
import { TaskModal } from "../components/TaskModal";
import { useAi } from "../contexts/ai-context";
import { useItemModal } from "../hooks/useItemModal";
import type { AIRelated, Item } from "../types/item";

interface Turn {
  id: number;
  question: string;
  pending: boolean;
  answer?: string;
  model?: string;
  sources?: AIRelated[];
  error?: string;
}

let nextId = 1;

export function AskView() {
  const { status } = useAi();
  const [question, setQuestion] = useState("");
  const [turns, setTurns] = useState<Turn[]>([]);
  const [titles, setTitles] = useState<string[]>([]);
  const bottomRef = useRef<HTMLDivElement>(null);

  const loadTitles = () =>
    itemsApi
      .list()
      .then((items) => setTitles(items.map((i) => i.title)))
      .catch(() => {});

  useEffect(() => {
    loadTitles();
  }, []);

  const { modalProps, openItem } = useItemModal({ titles, onChanged: loadTitles });

  const busy = turns.some((t) => t.pending);
  const ready = status?.enabled && status.chat_model_ready && status.embed_model_ready;

  const submit = async () => {
    const text = question.trim();
    if (!text || busy || !ready) return;
    const id = nextId++;
    setTurns((prev) => [...prev, { id, question: text, pending: true }]);
    setQuestion("");
    try {
      const result = await aiApi.ask(text);
      setTurns((prev) =>
        prev.map((t) =>
          t.id === id ? { ...t, pending: false, answer: result.answer, model: result.model, sources: result.sources } : t,
        ),
      );
    } catch (err) {
      setTurns((prev) =>
        prev.map((t) =>
          t.id === id
            ? { ...t, pending: false, error: err instanceof Error ? err.message : "The question failed." }
            : t,
        ),
      );
    }
    setTimeout(() => bottomRef.current?.scrollIntoView({ behavior: "smooth" }), 50);
  };

  const sourceItem = (turn: Turn, n: number): Item | undefined => turn.sources?.[n - 1]?.item;

  const unavailableReason = useMemo(() => {
    if (!status) return "Checking the local AI…";
    if (!status.enabled) return "Local AI is turned off.";
    if (!status.available) return "Ollama was not detected.";
    if (!status.chat_model_ready) return "No chat model is installed in Ollama (ollama pull llama3.2).";
    if (!status.embed_model_ready) return "No embedding model is installed in Ollama (ollama pull nomic-embed-text).";
    return null;
  }, [status]);

  return (
    <div className="mx-auto flex min-h-screen max-w-3xl flex-col px-6 py-8">
      <h1 className="text-2xl font-semibold text-[var(--text)]">Ask your notes</h1>
      <p className="mb-4 text-sm text-[var(--text-secondary)]">
        Questions are answered from your own notes and todos by a model running on this computer. Click
        a citation to check the source. Answers can be wrong, so verify anything important.
      </p>

      {unavailableReason && (
        <p className="mb-4 rounded-lg bg-amber-50 p-3 text-sm text-[var(--text)] dark:bg-amber-950">
          {unavailableReason}{" "}
          <Link to="/settings" className="text-primary underline">
            Open Settings
          </Link>
        </p>
      )}

      <div className="flex-1 space-y-5 pb-4">
        {turns.length === 0 && !unavailableReason && (
          <p className="py-10 text-center text-sm text-[var(--text-secondary)]">
            Try: "What did I decide about the trip?" or "Which todos relate to taxes?"
          </p>
        )}

        {turns.map((turn) => (
          <div key={turn.id} className="space-y-2">
            <p className="ml-auto w-fit max-w-[85%] rounded-xl bg-primary px-4 py-2 text-sm text-white">
              {turn.question}
            </p>
            <div className="max-w-[92%] rounded-xl border border-[var(--border)] bg-[var(--bg-elevated)] px-4 py-3">
              {turn.pending && (
                <p className="text-sm text-[var(--text-secondary)]">
                  Searching your notes… running on your computer, this can take a moment.
                </p>
              )}
              {turn.error && <p className="text-sm text-danger">{turn.error}</p>}
              {turn.answer !== undefined && (
                <>
                  <p className="whitespace-pre-wrap text-sm leading-relaxed text-[var(--text)]" data-testid="answer">
                    {turn.answer.split(/(\[\d+\])/g).map((part, i) => {
                      const match = /^\[(\d+)\]$/.exec(part);
                      const item = match ? sourceItem(turn, Number(match[1])) : undefined;
                      return item ? (
                        <button
                          key={i}
                          onClick={() => openItem(item)}
                          title={item.title}
                          className="mx-0.5 rounded bg-primary/10 px-1 text-xs font-semibold text-primary hover:bg-primary/20"
                        >
                          {match![1]}
                        </button>
                      ) : (
                        <span key={i}>{part}</span>
                      );
                    })}
                  </p>
                  {turn.sources && turn.sources.length > 0 && (
                    <div className="mt-3 border-t border-[var(--border)] pt-2">
                      <p className="mb-1 text-xs font-medium text-[var(--text-secondary)]">
                        Sources used{turn.model ? ` · ${turn.model}` : ""}
                      </p>
                      <div className="flex flex-wrap gap-2">
                        {turn.sources.map(({ item, score }, i) => (
                          <button
                            key={item.id}
                            onClick={() => openItem(item)}
                            className="rounded-full border border-[var(--border)] px-2.5 py-0.5 text-xs text-[var(--text)] hover:border-primary/50"
                          >
                            <span className="mr-1 font-semibold text-primary">{i + 1}</span>
                            {item.type === "NOTE" ? "📝" : "✓"} {item.title}
                            <span className="ml-1 opacity-60">{(score * 100).toFixed(0)}%</span>
                          </button>
                        ))}
                      </div>
                    </div>
                  )}
                </>
              )}
            </div>
          </div>
        ))}
        <div ref={bottomRef} />
      </div>

      <div className="sticky bottom-0 -mx-6 border-t border-[var(--border)] bg-[var(--bg)] px-6 py-4">
        <div className="flex gap-2">
          <textarea
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                submit();
              }
            }}
            rows={2}
            placeholder="Ask a question about your notes…"
            aria-label="Your question"
            disabled={!ready}
            className="flex-1 resize-none rounded-lg border border-[var(--border)] bg-[var(--bg-elevated)] px-3 py-2 text-sm text-[var(--text)] placeholder:text-[var(--text-secondary)] focus:outline-none focus:ring-2 focus:ring-primary disabled:opacity-60"
          />
          <Button onClick={submit} disabled={!ready || busy || !question.trim()}>
            {busy ? "Thinking…" : "Ask"}
          </Button>
        </div>
      </div>

      <TaskModal {...modalProps} />
    </div>
  );
}
