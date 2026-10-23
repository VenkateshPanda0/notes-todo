import { act, render, screen, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { itemsApi } from "../api/client";
import { AiContext } from "../contexts/ai-context";
import { makeItem } from "../test/fixtures";
import { Dashboard } from "./Dashboard";

beforeEach(() => {
  vi.useFakeTimers({ toFake: ["Date"] });
  vi.setSystemTime(new Date(2026, 9, 21, 12));
});
afterEach(() => {
  vi.useRealTimers();
});

async function renderView(view: "today" | "all" | "upcoming", items: ReturnType<typeof makeItem>[]) {
  vi.spyOn(itemsApi, "list").mockResolvedValue(items);
  render(
    <AiContext.Provider value={{ status: null, refresh: async () => {}, setStatus: () => {} }}>
      <MemoryRouter>
        <Dashboard view={view} />
      </MemoryRouter>
    </AiContext.Provider>,
  );
  await act(async () => {});
}

const items = [
  makeItem({ id: 1, title: "Overdue chore", due_date: "2026-10-18" }),
  makeItem({ id: 2, title: "Due today A", due_date: "2026-10-21" }),
  makeItem({ id: 3, title: "Due today done", due_date: "2026-10-21", completed: true }),
  makeItem({ id: 4, title: "Later", due_date: "2026-11-05" }),
  makeItem({ id: 5, title: "Old and finished", due_date: "2026-10-10", completed: true }),
  makeItem({ id: 6, title: "No date", due_date: null }),
  makeItem({ id: 7, title: "A note", type: "NOTE", due_date: null }),
];

describe("Today view", () => {
  it("lists overdue items in their own section ahead of today's", async () => {
    await renderView("today", items);

    const overdue = screen.getByRole("region", { name: "Overdue" });
    const today = screen.getByRole("region", { name: "Due today" });
    expect(within(overdue).getByText("Overdue chore")).toBeTruthy();
    expect(within(overdue).getByText(/Overdue · 1/)).toBeTruthy();
    expect(within(today).getByText("Due today A")).toBeTruthy();
    expect(within(today).getByText("Due today done")).toBeTruthy();
    expect(overdue.compareDocumentPosition(today) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  });

  it("puts the most overdue first, and today's items by priority with finished ones last", async () => {
    await renderView("today", [
      makeItem({ id: 1, title: "Overdue newer", due_date: "2026-10-20" }),
      makeItem({ id: 2, title: "Overdue oldest", due_date: "2026-10-01" }),
      makeItem({ id: 3, title: "Overdue middle", due_date: "2026-10-10" }),
      makeItem({ id: 4, title: "Today low", due_date: "2026-10-21", priority: "LOW" }),
      makeItem({ id: 5, title: "Today done", due_date: "2026-10-21", priority: "HIGH", completed: true }),
      makeItem({ id: 6, title: "Today high", due_date: "2026-10-21", priority: "HIGH" }),
      makeItem({ id: 7, title: "Today medium", due_date: "2026-10-21", priority: "MEDIUM" }),
    ]);

    const titles = (region: string) =>
      within(screen.getByRole("region", { name: region }))
        .getAllByRole("button")
        .filter((b) => b.className.includes("truncate"))
        .map((b) => b.textContent);
    expect(titles("Overdue")).toEqual(["Overdue oldest", "Overdue middle", "Overdue newer"]);
    expect(titles("Due today")).toEqual(["Today high", "Today medium", "Today low", "Today done"]);
  });

  it("leaves out upcoming, undated, finished-and-overdue items and notes", async () => {
    await renderView("today", items);

    for (const hidden of ["Later", "No date", "Old and finished", "A note"]) {
      expect(screen.queryByText(hidden)).toBeNull();
    }
  });

  it("shows a plain list (no section headings) when nothing is overdue", async () => {
    await renderView("today", [items[1]]);

    expect(screen.queryByRole("region", { name: "Overdue" })).toBeNull();
    expect(screen.getByText("Due today A")).toBeTruthy();
  });

  it("shows only the overdue section when nothing else is due today", async () => {
    await renderView("today", [items[0]]);

    expect(screen.getByRole("region", { name: "Overdue" })).toBeTruthy();
    expect(screen.queryByRole("region", { name: "Due today" })).toBeNull();
  });

  it("says so when there is nothing to do", async () => {
    await renderView("today", [items[3]]);

    expect(screen.getByText("Nothing here yet.")).toBeTruthy();
  });
});

describe("other views are unchanged", () => {
  it("Upcoming shows only future dates and never overdue ones", async () => {
    await renderView("upcoming", items);

    expect(screen.getByText("Later")).toBeTruthy();
    expect(screen.queryByText("Overdue chore")).toBeNull();
    expect(screen.queryByText("Due today A")).toBeNull();
  });

  it("All Tasks shows every todo without section headings", async () => {
    await renderView("all", items);

    expect(screen.getByText("Overdue chore")).toBeTruthy();
    expect(screen.getByText("No date")).toBeTruthy();
    expect(screen.queryByRole("region", { name: "Overdue" })).toBeNull();
    expect(screen.queryByText("A note")).toBeNull();
  });
});
