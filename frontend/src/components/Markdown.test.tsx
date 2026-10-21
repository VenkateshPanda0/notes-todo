import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { Markdown } from "./Markdown";

const known = new Set(["project atlas"]);

describe("Markdown component", () => {
  it("renders sanitized markdown", () => {
    render(<Markdown source={"# Hi\n\n<script>window.__x=1</script>\n\n**ok**"} knownTitles={known} onWikiLink={() => {}} />);
    expect(screen.getByRole("heading", { name: "Hi" })).toBeTruthy();
    expect(document.querySelector("script")).toBeNull();
    expect(screen.getByText("ok").tagName).toBe("STRONG");
  });

  it("reports the target title when a wiki-link is clicked and prevents navigation", () => {
    const onWikiLink = vi.fn();
    render(<Markdown source="see [[Project Atlas|the plan]]" knownTitles={known} onWikiLink={onWikiLink} />);
    const notPrevented = fireEvent.click(screen.getByText("the plan"));
    expect(onWikiLink).toHaveBeenCalledExactlyOnceWith("Project Atlas");
    expect(notPrevented).toBe(false); // default action (navigating to "#") was prevented
  });

  it("styles unresolved links differently", () => {
    render(<Markdown source="[[Ghost]]" knownTitles={known} onWikiLink={() => {}} />);
    expect(screen.getByText("Ghost").className).toContain("wikilink-missing");
  });

  it("ignores clicks on ordinary content and external links", () => {
    const onWikiLink = vi.fn();
    render(<Markdown source={"plain text\n\n[site](https://example.com)"} knownTitles={known} onWikiLink={onWikiLink} />);
    fireEvent.click(screen.getByText("plain text"));
    fireEvent.click(screen.getByText("site"));
    expect(onWikiLink).not.toHaveBeenCalled();
  });

  it("updates when the source changes", () => {
    const { rerender } = render(<Markdown source="first" knownTitles={known} onWikiLink={() => {}} />);
    rerender(<Markdown source="second" knownTitles={known} onWikiLink={() => {}} />);
    expect(screen.queryByText("first")).toBeNull();
    expect(screen.getByText("second")).toBeTruthy();
  });
});
