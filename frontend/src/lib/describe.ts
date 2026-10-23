import { describeRecurrence } from "./recurrence";
import type { QuickAddPreview } from "../types/item";

/** "Mon, Oct 26" from "2026-10-26", without the UTC shift `new Date("YYYY-MM-DD")` would cause. */
export function formatShortDate(dateStr: string): string {
  const [y, m, d] = dateStr.split("-").map(Number);
  return new Date(y, m - 1, d).toLocaleDateString(undefined, { weekday: "short", month: "short", day: "numeric" });
}

/** One line saying how Quick Add understood the text: "Todo · High · due Fri, Oct 23 · ↻ Weekly · #errands". */
export function describeParsed(preview: QuickAddPreview): string {
  const parts: string[] = [preview.type === "NOTE" ? "Note" : "Todo"];
  if (preview.type === "TODO") parts.push(preview.priority[0] + preview.priority.slice(1).toLowerCase());
  if (preview.due_date) parts.push(`due ${formatShortDate(preview.due_date)}`);
  if (preview.recurrence) parts.push(`↻ ${describeRecurrence(preview.recurrence)}`);
  if (preview.tags.length) parts.push(preview.tags.map((t) => `#${t}`).join(" "));
  return parts.join(" · ");
}
