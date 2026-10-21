/** Repeat rules, mirroring backend/app/services/recurrence.py: "3d", "1w", "2m", "1y" or "weekdays". */

export type RepeatUnit = "d" | "w" | "m" | "y";

export const UNIT_LABELS: Record<RepeatUnit, string> = {
  d: "day",
  w: "week",
  m: "month",
  y: "year",
};

export const PRESETS: { value: string; label: string }[] = [
  { value: "", label: "Does not repeat" },
  { value: "1d", label: "Daily" },
  { value: "weekdays", label: "Every weekday" },
  { value: "1w", label: "Weekly" },
  { value: "1m", label: "Monthly" },
  { value: "1y", label: "Yearly" },
];

const RULE = /^(\d{1,3})([dwmy])$/;

export function isPreset(rule: string): boolean {
  return PRESETS.some((p) => p.value === rule);
}

/** Split a rule into its interval and unit, or null for "", "weekdays" and anything unrecognised. */
export function parseRule(rule: string | null): { count: number; unit: RepeatUnit } | null {
  const match = rule ? RULE.exec(rule) : null;
  return match ? { count: Number(match[1]), unit: match[2] as RepeatUnit } : null;
}

/** Build a canonical rule from a count and unit; clamps the count to 1-365. */
export function buildRule(count: number, unit: RepeatUnit): string {
  const clamped = Math.min(365, Math.max(1, Math.round(Number.isFinite(count) ? count : 1)));
  return `${clamped}${unit}`;
}

/** Human description: "1w" -> "Weekly", "2w" -> "Every 2 weeks", null -> "Does not repeat". */
export function describeRecurrence(rule: string | null | undefined): string {
  if (!rule) return "Does not repeat";
  const preset = PRESETS.find((p) => p.value === rule);
  if (preset) return preset.label;
  const parsed = parseRule(rule);
  if (!parsed) return rule;
  return `Every ${parsed.count} ${UNIT_LABELS[parsed.unit]}s`;
}
