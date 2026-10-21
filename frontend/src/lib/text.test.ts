import { describe, expect, it } from "vitest";
import { snippet } from "./text";

describe("snippet", () => {
  it("returns the first non-empty line", () => {
    expect(snippet("\n\n  Hello world\nsecond line")).toBe("Hello world");
  });

  it("strips heading, quote and list markers", () => {
    expect(snippet("# Heading")).toBe("Heading");
    expect(snippet("> quoted")).toBe("quoted");
    expect(snippet("- item")).toBe("item");
    expect(snippet("* item")).toBe("item");
    expect(snippet("### Deep")).toBe("Deep");
  });

  it("strips emphasis and code markers but keeps the words", () => {
    expect(snippet("**bold** and _italic_ and `code`")).toBe("bold and italic and code");
  });

  it("copes with empty content", () => {
    expect(snippet("")).toBe("");
    expect(snippet("   \n  ")).toBe("");
  });
});
