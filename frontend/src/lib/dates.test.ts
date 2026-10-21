import { afterEach, describe, expect, it, vi } from "vitest";
import { isToday, isUpcoming, localDateString } from "./dates";

afterEach(() => {
  vi.useRealTimers();
});

describe("localDateString", () => {
  it("formats local year, month and day with zero padding", () => {
    expect(localDateString(new Date(2026, 0, 5))).toBe("2026-01-05");
    expect(localDateString(new Date(2026, 11, 31))).toBe("2026-12-31");
  });

  it("uses the LOCAL date, not UTC, late in the evening", () => {
    // 23:30 local on 21 Oct is already 22 Oct in UTC for anyone east of Greenwich, and still
    // 21 Oct locally. The helper must report the local day wherever the tests run.
    const lateEvening = new Date(2026, 9, 21, 23, 30);
    expect(localDateString(lateEvening)).toBe("2026-10-21");
  });

  it("uses the LOCAL date, not UTC, just after midnight", () => {
    const justAfterMidnight = new Date(2026, 9, 22, 0, 15);
    expect(localDateString(justAfterMidnight)).toBe("2026-10-22");
  });
});

describe("isToday / isUpcoming", () => {
  const at = (y: number, m: number, d: number, h = 12) => vi.setSystemTime(new Date(y, m, d, h));

  it("compares against today's local date", () => {
    vi.useFakeTimers();
    at(2026, 9, 21);
    expect(isToday("2026-10-21")).toBe(true);
    expect(isToday("2026-10-20")).toBe(false);
    expect(isToday("2026-10-22")).toBe(false);
  });

  it("is still today at 23:59 and tomorrow at 00:00", () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date(2026, 9, 21, 23, 59));
    expect(isToday("2026-10-21")).toBe(true);
    vi.setSystemTime(new Date(2026, 9, 22, 0, 0));
    expect(isToday("2026-10-21")).toBe(false);
    expect(isToday("2026-10-22")).toBe(true);
  });

  it("treats only strictly later dates as upcoming", () => {
    vi.useFakeTimers();
    at(2026, 9, 21);
    expect(isUpcoming("2026-10-22")).toBe(true);
    expect(isUpcoming("2027-01-01")).toBe(true);
    expect(isUpcoming("2026-10-21")).toBe(false);
    expect(isUpcoming("2026-10-20")).toBe(false);
  });

  it("handles month and year boundaries", () => {
    vi.useFakeTimers();
    at(2026, 11, 31);
    expect(isUpcoming("2027-01-01")).toBe(true);
    expect(isToday("2026-12-31")).toBe(true);
  });

  it("treats missing dates as neither today nor upcoming", () => {
    expect(isToday(null)).toBe(false);
    expect(isUpcoming(null)).toBe(false);
  });
});
