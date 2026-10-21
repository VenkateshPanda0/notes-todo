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
