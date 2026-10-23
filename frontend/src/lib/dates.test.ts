import { afterEach, describe, expect, it, vi } from "vitest";
import { countDue, isOverdue, isToday, isUpcoming, localDateString } from "./dates";

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


describe("isOverdue", () => {
  it("is true only for dates strictly before today", () => {
    vi.useFakeTimers({ toFake: ["Date"] });
    vi.setSystemTime(new Date(2026, 9, 21, 12));
    expect(isOverdue("2026-10-20")).toBe(true);
    expect(isOverdue("2025-01-01")).toBe(true);
    expect(isOverdue("2026-10-21")).toBe(false);
    expect(isOverdue("2026-10-22")).toBe(false);
    expect(isOverdue(null)).toBe(false);
  });

  it("rolls over at midnight", () => {
    vi.useFakeTimers({ toFake: ["Date"] });
    vi.setSystemTime(new Date(2026, 9, 21, 23, 59));
    expect(isOverdue("2026-10-21")).toBe(false);
    vi.setSystemTime(new Date(2026, 9, 22, 0, 1));
    expect(isOverdue("2026-10-21")).toBe(true);
  });
});

describe("countDue", () => {
  const todo = (due_date: string | null, completed = false, type = "TODO") => ({ type, completed, due_date });

  it("counts open todos due today and overdue ones separately", () => {
    vi.useFakeTimers({ toFake: ["Date"] });
    vi.setSystemTime(new Date(2026, 9, 21, 12));

    const counts = countDue([
      todo("2026-10-21"),
      todo("2026-10-21"),
      todo("2026-10-20"),
      todo("2026-09-01"),
      todo("2026-10-22"), // upcoming: not counted
      todo(null), // undated: not counted
    ]);

    expect(counts).toEqual({ today: 2, overdue: 2 });
  });

  it("ignores completed todos and notes", () => {
    vi.useFakeTimers({ toFake: ["Date"] });
    vi.setSystemTime(new Date(2026, 9, 21, 12));

    expect(countDue([todo("2026-10-21", true), todo("2026-10-20", true), todo("2026-10-21", false, "NOTE")])).toEqual({
      today: 0,
      overdue: 0,
    });
  });

  it("handles an empty list", () => {
    expect(countDue([])).toEqual({ today: 0, overdue: 0 });
  });
});
