/** The device's local calendar date as YYYY-MM-DD (not UTC, which can be a day off near midnight). */
export function localDateString(d: Date): string {
  const year = d.getFullYear();
  const month = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

export function isToday(dateStr: string | null): boolean {
  if (!dateStr) return false;
  return dateStr === localDateString(new Date());
}

export function isUpcoming(dateStr: string | null): boolean {
  if (!dateStr) return false;
  return dateStr > localDateString(new Date());
}

export function isOverdue(dateStr: string | null): boolean {
  if (!dateStr) return false;
  return dateStr < localDateString(new Date());
}

/** How many open todos need attention today: due today, and already overdue. */
export function countDue(items: { type: string; completed: boolean; due_date: string | null }[]): {
  today: number;
  overdue: number;
} {
  let today = 0;
  let overdue = 0;
  for (const item of items) {
    if (item.type !== "TODO" || item.completed) continue;
    if (isToday(item.due_date)) today += 1;
    else if (isOverdue(item.due_date)) overdue += 1;
  }
  return { today, overdue };
}
