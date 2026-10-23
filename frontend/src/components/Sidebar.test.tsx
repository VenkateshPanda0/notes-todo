import { act, render, screen, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { itemsApi } from "../api/client";
import { AiContext } from "../contexts/ai-context";
import { notifyItemsChanged } from "../lib/events";
import { makeItem } from "../test/fixtures";
import { Sidebar } from "./Sidebar";

const NOW = new Date(2026, 9, 21, 12);

beforeEach(() => {
  vi.useFakeTimers({ toFake: ["Date", "setTimeout", "clearTimeout", "setInterval", "clearInterval"] });
  vi.setSystemTime(NOW);
});
afterEach(() => {
  vi.useRealTimers();
});

async function renderSidebar(items = [] as ReturnType<typeof makeItem>[], aiEnabled = false) {
  const list = vi.spyOn(itemsApi, "list").mockResolvedValue(items);
  render(
    <AiContext.Provider
      value={{ status: aiEnabled ? ({ enabled: true } as never) : null, refresh: async () => {}, setStatus: () => {} }}
    >
      <MemoryRouter>
        <Sidebar />
      </MemoryRouter>
    </AiContext.Provider>,
  );
  await act(async () => {});
  return list;
}

describe("Sidebar", () => {
  it("has a labelled main navigation with every view", async () => {
    await renderSidebar();

    const nav = within(screen.getByRole("navigation", { name: "Main" }));
    for (const name of ["All Tasks", "Today", "Upcoming", "Completed", "Notes", "Calendar", "Graph"]) {
      expect(nav.getByRole("link", { name })).toBeTruthy();
    }
    expect(screen.queryByRole("link", { name: "Ask your notes" })).toBeNull();
  });

  it("only offers 'Ask your notes' when local AI is on", async () => {
    await renderSidebar([], true);

    expect(screen.getByRole("link", { name: "Ask your notes" })).toBeTruthy();
  });

  it("shows no badge when nothing needs attention", async () => {
    await renderSidebar([makeItem({ due_date: "2026-12-01" })]);

    expect(screen.queryByTestId("today-badge")).toBeNull();
    expect(screen.getByRole("link", { name: "Today" })).toBeTruthy();
  });

  it("badges Today with items due today plus overdue, and says so to screen readers", async () => {
    await renderSidebar([
      makeItem({ id: 1, due_date: "2026-10-21" }),
      makeItem({ id: 2, due_date: "2026-10-21" }),
      makeItem({ id: 3, due_date: "2026-10-19" }),
      makeItem({ id: 4, due_date: "2026-11-30" }),
      makeItem({ id: 5, due_date: "2026-10-21", completed: true }),
    ]);

    expect(screen.getByTestId("today-badge").textContent).toBe("3");
    expect(screen.getByRole("link", { name: "Today, 2 due today, 1 overdue" })).toBeTruthy();
  });

  it("only mentions what applies", async () => {
    await renderSidebar([makeItem({ due_date: "2026-10-10" })]);

    expect(screen.getByRole("link", { name: "Today, 1 overdue" })).toBeTruthy();
  });

  it("asks only for open todos", async () => {
    const list = await renderSidebar();

    expect(list).toHaveBeenCalledWith({ type: "TODO", completed: false });
  });

  it("refreshes right after items change anywhere in the app", async () => {
    const list = await renderSidebar([]);
    expect(screen.queryByTestId("today-badge")).toBeNull();
    list.mockResolvedValue([makeItem({ due_date: "2026-10-21" })]);

    act(() => notifyItemsChanged());
    await act(async () => {
      await vi.advanceTimersByTimeAsync(200);
    });

    expect(screen.getByTestId("today-badge").textContent).toBe("1");
  });

  it("collapses a burst of changes into one request", async () => {
    const list = await renderSidebar([]);
    list.mockClear();

    act(() => {
      for (let i = 0; i < 10; i++) notifyItemsChanged();
    });
    await act(async () => {
      await vi.advanceTimersByTimeAsync(400);
    });

    expect(list).toHaveBeenCalledTimes(1);
  });

  it("re-checks when the window regains focus and periodically (the date can roll over)", async () => {
    const list = await renderSidebar([]);
    list.mockClear();

    act(() => window.dispatchEvent(new Event("focus")));
    await act(async () => {
      await vi.advanceTimersByTimeAsync(200);
    });
    expect(list).toHaveBeenCalledTimes(1);

    list.mockClear();
    await act(async () => {
      await vi.advanceTimersByTimeAsync(5 * 60 * 1000 + 100);
    });
    expect(list).toHaveBeenCalled();
  });

  it("survives a failing request", async () => {
    vi.spyOn(itemsApi, "list").mockRejectedValue(new Error("offline"));
    render(
      <AiContext.Provider value={{ status: null, refresh: async () => {}, setStatus: () => {} }}>
        <MemoryRouter>
          <Sidebar />
        </MemoryRouter>
      </AiContext.Provider>,
    );
    await act(async () => {});

    expect(screen.getByRole("link", { name: "Today" })).toBeTruthy();
  });
});
