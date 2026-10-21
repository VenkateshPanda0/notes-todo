import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { makeItem } from "../test/fixtures";
import { TaskRow } from "./TaskRow";

function setup(item = makeItem()) {
  const onToggleComplete = vi.fn();
  const onClick = vi.fn();
  render(<TaskRow item={item} onToggleComplete={onToggleComplete} onClick={onClick} />);
  return { onToggleComplete, onClick };
}

describe("TaskRow", () => {
  it("shows title, priority and a short due date", () => {
    setup();
    expect(screen.getByRole("button", { name: "Pay rent" })).toBeTruthy();
    expect(screen.getByText("High")).toBeTruthy();
    expect(screen.getByText(/Nov/)).toBeTruthy();
  });

  it("opens the item from the title button (keyboard path) exactly once", () => {
    const { onClick } = setup();
    fireEvent.click(screen.getByRole("button", { name: "Pay rent" }));
    expect(onClick).toHaveBeenCalledTimes(1);
    expect(onClick.mock.calls[0][0].title).toBe("Pay rent");
  });

  it("opens the item when the row itself is clicked (mouse path)", () => {
    const { onClick } = setup();
    fireEvent.click(screen.getByRole("button", { name: "Pay rent" }).closest("div")!.parentElement!);
    expect(onClick).toHaveBeenCalledTimes(1);
  });

  it("toggles completion from the checkbox without opening the item", () => {
    const { onToggleComplete, onClick } = setup();
    fireEvent.click(screen.getByRole("checkbox", { name: 'Complete "Pay rent"' }));
    expect(onToggleComplete).toHaveBeenCalledTimes(1);
    expect(onClick).not.toHaveBeenCalled();
  });

  it("labels the checkbox for the current state", () => {
    setup(makeItem({ completed: true }));
    expect(screen.getByRole("checkbox", { name: 'Reopen "Pay rent"' })).toBeTruthy();
  });

  it("shows up to three tags and counts the rest", () => {
    setup(makeItem({ tags: ["a", "b", "c", "d", "e"] }));
    expect(screen.getByText("#a")).toBeTruthy();
    expect(screen.getByText("#c")).toBeTruthy();
    expect(screen.queryByText("#d")).toBeNull();
    expect(screen.getByText("+2")).toBeTruthy();
  });

  it("shows a content snippet for notes but not priority", () => {
    setup(makeItem({ type: "NOTE", title: "Ideas", content: "## Big idea\nmore", due_date: null }));
    expect(screen.getByText("Big idea")).toBeTruthy();
    expect(screen.queryByText("High")).toBeNull();
  });
});
