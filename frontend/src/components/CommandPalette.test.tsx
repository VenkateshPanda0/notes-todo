import { act, fireEvent, render, screen, within } from "@testing-library/react";
import { MemoryRouter, useLocation } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { itemsApi } from "../api/client";
import { AiContext } from "../contexts/ai-context";
import { makeItem } from "../test/fixtures";
import { CommandPalette } from "./CommandPalette";

const items = [
  makeItem({ id: 1, title: "Pay rent", type: "TODO", updated_at: "2026-10-20T00:00:00" }),
  makeItem({ id: 2, title: "Trip ideas", type: "NOTE", content: "Visit Kyoto in spring", due_date: null, updated_at: "2026-10-21T00:00:00" }),
  makeItem({ id: 3, title: "Taxes", type: "TODO", completed: true, updated_at: "2026-10-01T00:00:00" }),
];

const parsed = { title: "call dentist", type: "TODO" as const, priority: "HIGH" as const, due_date: "2026-10-23", recurrence: null, tags: ["errands"] };

function Where() {
  return <div data-testid="where">{useLocation().pathname}</div>;
}

async function setup({ ai = false, list = items }: { ai?: boolean; list?: typeof items } = {}) {
  const listSpy = vi.spyOn(itemsApi, "list").mockResolvedValue(list);
  vi.spyOn(itemsApi, "backlinks").mockResolvedValue([]);
  render(
    <AiContext.Provider value={{ status: ai ? ({ enabled: true } as never) : null, refresh: async () => {}, setStatus: () => {} }}>
      <MemoryRouter initialEntries={["/notes"]}>
        <button>opener</button>
        <CommandPalette />
        <Where />
      </MemoryRouter>
    </AiContext.Provider>,
  );
  await act(async () => {});
  return { listSpy };
}

const press = async (init: KeyboardEventInit) => {
  await act(async () => {
    fireEvent.keyDown(window, init);
  });
};
const openPalette = async () => press({ key: "k", ctrlKey: true });
const box = () => screen.getByRole("combobox", { name: "Search, jump, or add" }) as HTMLInputElement;
const typeIn = async (value: string) => {
  await act(async () => {
    fireEvent.change(box(), { target: { value } });
    await vi.advanceTimersByTimeAsync(250); // past the debounce
  });
};
const keyInBox = async (key: string) => {
  await act(async () => {
    fireEvent.keyDown(box(), { key });
  });
};
const optionNames = () => screen.getAllByRole("option").map((o) => o.textContent ?? "");

beforeEach(() => {
  vi.useFakeTimers({ toFake: ["setTimeout", "clearTimeout"] });
});
afterEach(() => {
  vi.useRealTimers();
});

describe("opening and closing", () => {
  it("is closed until Ctrl+K, and also opens with Cmd+K", async () => {
    await setup();
    expect(screen.queryByRole("dialog", { name: "Command palette" })).toBeNull();

    await openPalette();
    expect(screen.getByRole("dialog", { name: "Command palette" })).toBeTruthy();
    expect(document.activeElement).toBe(box());

    await press({ key: "k", ctrlKey: true });
    expect(screen.queryByRole("dialog", { name: "Command palette" })).toBeNull();
    await press({ key: "K", metaKey: true });
    expect(screen.getByRole("dialog", { name: "Command palette" })).toBeTruthy();
  });

  it("ignores a plain 'k'", async () => {
    await setup();
    await press({ key: "k" });
    expect(screen.queryByRole("dialog")).toBeNull();
  });

  it("Escape closes it and focus returns to where it was", async () => {
    await setup();
    screen.getByRole("button", { name: "opener" }).focus();
    await openPalette();

    await keyInBox("Escape");

    expect(screen.queryByRole("dialog", { name: "Command palette" })).toBeNull();
    expect(document.activeElement).toBe(screen.getByRole("button", { name: "opener" }));
  });

  it("clicking the backdrop closes it, clicking inside does not", async () => {
    await setup();
    await openPalette();

    fireEvent.mouseDown(screen.getByRole("dialog", { name: "Command palette" }));
    expect(screen.getByRole("dialog", { name: "Command palette" })).toBeTruthy();
    fireEvent.mouseDown(screen.getByRole("dialog", { name: "Command palette" }).parentElement!);
    expect(screen.queryByRole("dialog", { name: "Command palette" })).toBeNull();
  });

  it("keeps Tab inside the palette", async () => {
    await setup();
    await openPalette();

    const prevented = !fireEvent.keyDown(box(), { key: "Tab" });

    expect(prevented).toBe(true);
  });

  it("starts fresh each time it is opened", async () => {
    await setup();
    await openPalette();
    await typeIn("rent");
    await keyInBox("Escape");

    await openPalette();

    expect(box().value).toBe("");
  });
});

describe("results", () => {
  it("shows pages and the most recently changed items when empty", async () => {
    await setup();
    await openPalette();

    const names = optionNames();
    expect(names[0]).toContain("Go to All Tasks");
    expect(names).toContain("Keyboard shortcuts" + "Help");
    expect(names.some((n) => n.includes("Trip ideas"))).toBe(true);
    const itemRows = names.filter((n) => n.includes("📝") || n.includes("✓"));
    expect(itemRows[0]).toContain("Trip ideas"); // newest update first
  });

  it("offers 'Ask your notes' only when local AI is on", async () => {
    await setup({ ai: false });
    await openPalette();
    expect(optionNames().some((n) => n.includes("Ask your notes"))).toBe(false);
  });

  it("includes 'Ask your notes' with AI on", async () => {
    await setup({ ai: true });
    await openPalette();
    expect(optionNames().some((n) => n.includes("Go to Ask your notes"))).toBe(true);
  });

  it("filters pages by name and by keyword", async () => {
    await setup();
    await openPalette();

    await typeIn("sett");
    expect(optionNames().some((n) => n.startsWith("Go to Settings"))).toBe(true);
    expect(optionNames().some((n) => n.startsWith("Go to Calendar"))).toBe(false);

    await typeIn("encryption"); // a keyword of Settings
    expect(optionNames().some((n) => n.startsWith("Go to Settings"))).toBe(true);
  });

  it("finds items by title and by content", async () => {
    await setup();
    await openPalette();

    await typeIn("kyoto");
    expect(optionNames().some((n) => n.includes("Trip ideas"))).toBe(true);
    expect(optionNames().some((n) => n.includes("Pay rent"))).toBe(false);
  });

  it("says when nothing matches (and still offers to add it)", async () => {
    await setup();
    await openPalette();

    await typeIn("zzzz-nothing");

    expect(optionNames()[0]).toContain("Add");
    expect(optionNames().some((n) => n.includes("Pay rent"))).toBe(false);
  });

  it("is an accessible combobox over a listbox with one selected option", async () => {
    await setup();
    await openPalette();

    expect(screen.getByRole("listbox", { name: "Results" })).toBeTruthy();
    const selected = screen.getAllByRole("option").filter((o) => o.getAttribute("aria-selected") === "true");
    expect(selected).toHaveLength(1);
    expect(box().getAttribute("aria-activedescendant")).toBe(selected[0].id);
    expect(box().getAttribute("aria-controls")).toBe(screen.getByRole("listbox").id);
  });
});

describe("keyboard navigation", () => {
  it("arrow keys move the selection and wrap around", async () => {
    await setup();
    await openPalette();
    const selectedIndex = () => screen.getAllByRole("option").findIndex((o) => o.getAttribute("aria-selected") === "true");
    const count = screen.getAllByRole("option").length;
    expect(selectedIndex()).toBe(0);

    await keyInBox("ArrowDown");
    expect(selectedIndex()).toBe(1);
    await keyInBox("ArrowUp");
    await keyInBox("ArrowUp");
    expect(selectedIndex()).toBe(count - 1);
    await keyInBox("ArrowDown");
    expect(selectedIndex()).toBe(0);
  });

  it("Enter on a page navigates there and closes", async () => {
    await setup();
    await openPalette();
    await typeIn("calendar");

    await keyInBox("ArrowDown"); // row 0 is "Add ...", row 1 is the page
    await keyInBox("Enter");

    expect(screen.getByTestId("where").textContent).toBe("/calendar");
    expect(screen.queryByRole("dialog", { name: "Command palette" })).toBeNull();
  });

  it("clicking a result works like Enter", async () => {
    await setup();
    await openPalette();

    await act(async () => {
      fireEvent.click(screen.getByRole("option", { name: /Go to Graph/ }));
    });

    expect(screen.getByTestId("where").textContent).toBe("/graph");
  });

  it("Enter on an item opens it in the editor", async () => {
    await setup();
    await openPalette();
    await typeIn("pay rent");

    await act(async () => {
      fireEvent.click(screen.getByRole("option", { name: /Pay rent/ }));
    });

    const editor = screen.getByRole("dialog", { name: /Edit Task/ });
    expect((within(editor).getByLabelText("Title") as HTMLInputElement).value).toBe("Pay rent");
    expect(screen.queryByRole("dialog", { name: "Command palette" })).toBeNull();
  });
});

describe("capture", () => {
  it("offers to add what you type and previews how it will be understood", async () => {
    const parse = vi.spyOn(itemsApi, "parse").mockResolvedValue(parsed);
    await setup();
    await openPalette();

    await typeIn("call dentist tomorrow !high #errands");

    expect(parse).toHaveBeenCalledWith("call dentist tomorrow !high #errands");
    const first = screen.getAllByRole("option")[0];
    expect(first.textContent).toContain("call dentist tomorrow !high #errands");
    expect(first.textContent).toMatch(/Todo · High · due .*Oct.* · #errands/);
  });

  it("creates the parsed item on Enter, announces it, closes and refreshes", async () => {
    vi.spyOn(itemsApi, "parse").mockResolvedValue(parsed);
    const create = vi.spyOn(itemsApi, "create").mockResolvedValue(makeItem({ id: 9, title: "call dentist" }));
    const { listSpy } = await setup();
    await openPalette();
    await typeIn("call dentist tomorrow");
    listSpy.mockClear();

    await keyInBox("Enter");

    expect(create).toHaveBeenCalledWith({
      title: "call dentist",
      type: "TODO",
      priority: "HIGH",
      due_date: "2026-10-23",
      recurrence: null,
      tags: ["errands"],
    });
    expect(screen.queryByRole("dialog", { name: "Command palette" })).toBeNull();
    expect(screen.getByRole("status").textContent).toBe("Added todo: call dentist");
    expect(listSpy).toHaveBeenCalled();
  });

  it("announces notes as notes", async () => {
    vi.spyOn(itemsApi, "parse").mockResolvedValue({ ...parsed, type: "NOTE", title: "wifi password" });
    vi.spyOn(itemsApi, "create").mockResolvedValue(makeItem({ type: "NOTE" }));
    await setup();
    await openPalette();
    await typeIn("note: wifi password");

    await keyInBox("Enter");

    expect(screen.getByRole("status").textContent).toBe("Added note: wifi password");
  });

  it("keeps the palette open and shows the error if saving fails", async () => {
    vi.spyOn(itemsApi, "parse").mockResolvedValue(parsed);
    vi.spyOn(itemsApi, "create").mockRejectedValue(new Error("Server exploded"));
    await setup();
    await openPalette();
    await typeIn("call dentist");

    await keyInBox("Enter");

    expect(screen.getByText("Server exploded")).toBeTruthy();
    expect(screen.getByRole("dialog", { name: "Command palette" })).toBeTruthy();
    expect(box().value).toBe("call dentist");
  });

  it("offers no capture row for an empty query", async () => {
    await setup();
    await openPalette();

    expect(optionNames().some((n) => n.startsWith("Add"))).toBe(false);
  });
});

describe("keyboard shortcut help", () => {
  it("lists the shortcuts, Esc goes back, and a second Esc closes", async () => {
    await setup();
    await openPalette();
    await act(async () => {
      fireEvent.click(screen.getByRole("option", { name: /Keyboard shortcuts/ }));
    });

    expect(screen.getByText("Ctrl / ⌘ + K")).toBeTruthy();
    expect(screen.getByText("Focus Quick Add on a task list")).toBeTruthy();
    expect(screen.queryByRole("listbox")).toBeNull();

    await keyInBox("Escape");
    expect(screen.getByRole("listbox", { name: "Results" })).toBeTruthy();
    await keyInBox("Escape");
    expect(screen.queryByRole("dialog", { name: "Command palette" })).toBeNull();
  });
});
