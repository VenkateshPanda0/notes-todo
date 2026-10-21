import { describe, expect, it } from "vitest";
import { PRESETS, buildRule, describeRecurrence, isPreset, parseRule } from "./recurrence";

describe("describeRecurrence", () => {
  it.each([
    [null, "Does not repeat"],
    [undefined, "Does not repeat"],
    ["", "Does not repeat"],
    ["1d", "Daily"],
    ["1w", "Weekly"],
    ["1m", "Monthly"],
    ["1y", "Yearly"],
    ["weekdays", "Every weekday"],
    ["3d", "Every 3 days"],
    ["2w", "Every 2 weeks"],
    ["6m", "Every 6 months"],
    ["2y", "Every 2 years"],
  ])("%s -> %s", (rule, text) => {
    expect(describeRecurrence(rule)).toBe(text);
  });

  it("falls back to the raw text for rules it doesn't understand", () => {
    expect(describeRecurrence("whenever")).toBe("whenever");
  });
});

describe("parseRule / buildRule", () => {
  it("parses count and unit", () => {
    expect(parseRule("12m")).toEqual({ count: 12, unit: "m" });
    expect(parseRule("1d")).toEqual({ count: 1, unit: "d" });
  });

  it("returns null for no rule, weekdays and garbage", () => {
    expect(parseRule(null)).toBeNull();
    expect(parseRule("")).toBeNull();
    expect(parseRule("weekdays")).toBeNull();
    expect(parseRule("x2")).toBeNull();
    expect(parseRule("1000d")).toBeNull();
  });

  it("builds canonical rules and clamps the interval", () => {
    expect(buildRule(3, "w")).toBe("3w");
    expect(buildRule(0, "d")).toBe("1d");
    expect(buildRule(-5, "d")).toBe("1d");
    expect(buildRule(9999, "y")).toBe("365y");
    expect(buildRule(2.6, "m")).toBe("3m");
    expect(buildRule(Number.NaN, "w")).toBe("1w");
  });

  it("round-trips", () => {
    for (const rule of ["1d", "2w", "6m", "3y"]) {
      const parsed = parseRule(rule)!;
      expect(buildRule(parsed.count, parsed.unit)).toBe(rule);
    }
  });
});

describe("presets", () => {
  it("knows which rules are presets", () => {
    expect(isPreset("")).toBe(true);
    expect(isPreset("1w")).toBe(true);
    expect(isPreset("weekdays")).toBe(true);
    expect(isPreset("2w")).toBe(false);
  });

  it("starts with 'Does not repeat' so the default is no repeat", () => {
    expect(PRESETS[0]).toEqual({ value: "", label: "Does not repeat" });
  });
});
