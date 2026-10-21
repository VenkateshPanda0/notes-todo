import { act, fireEvent, render, screen } from "@testing-library/react";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { itemsApi } from "../api/client";
import { AiContext } from "../contexts/ai-context";
import { makeItem } from "../test/fixtures";
import type { Item } from "../types/item";
import { TaskModal } from "./TaskModal";

const withAi = (ui: ReactNode) => (
  <AiContext.Provider value={{ status: null, refresh: async () => {}, setStatus: () => {} }}>{ui}</AiContext.Provider>
);

function setup(initial: Item | null, defaultType: "TODO" | "NOTE" = "TODO") {
  const onSave = vi.fn().mockResolvedValue(undefined);
  const onClose = vi.fn();
  render(withAi(<TaskModal open initial={initial} defaultType={defaultType} onClose={onClose} onSave={onSave} />));
  return { onSave, onClose };
}

const repeatSelect = () => screen.getByLabelText("Repeat") as HTMLSelectElement;
const save = async () => {
  await act(async () => {
    fireEvent.click(screen.getByRole("button", { name: /Create Task|Create Note|Save Changes/ }));
  });
};

beforeEach(() => {
  vi.spyOn(itemsApi, "backlinks").mockResolvedValue([]);
});

describe("TaskModal repeat control", () => {
  it("defaults to not repeating and saves null", async () => {
    const { onSave } = setup(null);
    fireEvent.change(screen.getByLabelText("Title"), { target: { value: "Water plants" } });

    expect(repeatSelect().value).toBe("");
    await save();

    expect(onSave.mock.calls[0][0].recurrence).toBeNull();
  });

  it("saves a preset rule", async () => {
    const { onSave } = setup(null);
    fireEvent.change(screen.getByLabelText("Title"), { target: { value: "Water plants" } });
    fireEvent.change(repeatSelect(), { target: { value: "1w" } });

    await save();

    expect(onSave.mock.calls[0][0].recurrence).toBe("1w");
  });

  it("explains what repeating does, and that it starts today without a due date", () => {
    setup(null);
    fireEvent.change(repeatSelect(), { target: { value: "1m" } });

    expect(screen.getByText(/Monthly: completing this task creates the next one, starting from today/)).toBeTruthy();

    fireEvent.change(screen.getByLabelText("Due Date"), { target: { value: "2026-11-01" } });

    expect(screen.getByText(/Monthly: completing this task creates the next one\./)).toBeTruthy();
  });

  it("opens an existing preset rule selected", () => {
    setup(makeItem({ recurrence: "weekdays" }));

    expect(repeatSelect().value).toBe("weekdays");
    expect(screen.queryByLabelText("Repeat interval")).toBeNull();
  });

  it("opens an existing custom rule in the interval editor", () => {
    setup(makeItem({ recurrence: "3m" }));

    expect(repeatSelect().value).toBe("custom");
    expect((screen.getByLabelText("Repeat interval") as HTMLInputElement).value).toBe("3");
    expect((screen.getByLabelText("Repeat unit") as HTMLSelectElement).value).toBe("m");
  });

  it("builds a custom rule from the interval and unit", async () => {
    const { onSave } = setup(null);
    fireEvent.change(screen.getByLabelText("Title"), { target: { value: "Gym" } });
    fireEvent.change(repeatSelect(), { target: { value: "custom" } });

    expect((screen.getByLabelText("Repeat interval") as HTMLInputElement).value).toBe("2"); // sensible start: every 2 weeks
    fireEvent.change(screen.getByLabelText("Repeat interval"), { target: { value: "5" } });
    fireEvent.change(screen.getByLabelText("Repeat unit"), { target: { value: "d" } });
    await save();

    expect(onSave.mock.calls[0][0].recurrence).toBe("5d");
  });

  it("clamps silly intervals", async () => {
    const { onSave } = setup(null);
    fireEvent.change(screen.getByLabelText("Title"), { target: { value: "x" } });
    fireEvent.change(repeatSelect(), { target: { value: "custom" } });
    fireEvent.change(screen.getByLabelText("Repeat interval"), { target: { value: "0" } });
    await save();

    expect(onSave.mock.calls[0][0].recurrence).toBe("1w");
  });

  it("can switch a custom rule back to a preset or to none", async () => {
    const { onSave } = setup(makeItem({ recurrence: "3m" }));

    fireEvent.change(repeatSelect(), { target: { value: "" } });
    expect(screen.queryByLabelText("Repeat interval")).toBeNull();
    await save();

    expect(onSave.mock.calls[0][0].recurrence).toBeNull();
  });

  it("is hidden for notes and never saves a rule for them", async () => {
    const { onSave } = setup(null, "NOTE");
    fireEvent.change(screen.getByLabelText("Title"), { target: { value: "An idea" } });

    expect(screen.queryByLabelText("Repeat")).toBeNull();
    await save();

    expect(onSave.mock.calls[0][0].recurrence).toBeNull();
  });

  it("drops the rule when a repeating todo is switched to a note", async () => {
    const { onSave } = setup(makeItem({ recurrence: "1w" }));

    fireEvent.click(screen.getByRole("button", { name: "Note" }));
    await save();

    expect(onSave.mock.calls[0][0]).toMatchObject({ type: "NOTE", recurrence: null });
  });

  it("counts a changed rule as an unsaved change when following a link", () => {
    const confirm = vi.spyOn(window, "confirm").mockReturnValue(false);
    const onOpenLink = vi.fn();
    const withLink = makeItem({ type: "TODO", content: "see [[Other]]", recurrence: "1w" });
    render(withAi(<TaskModal open initial={withLink} onClose={() => {}} onSave={vi.fn()} onOpenLink={onOpenLink} />));
    fireEvent.change(repeatSelect(), { target: { value: "1d" } });

    fireEvent.click(screen.getByRole("button", { name: "Preview" }));
    fireEvent.click(screen.getByText("Other"));

    expect(confirm).toHaveBeenCalled();
    expect(onOpenLink).not.toHaveBeenCalled();
  });
});

describe("TaskModal dialog behaviour", () => {
  it("is a labelled modal dialog", () => {
    setup(null);

    const dialog = screen.getByRole("dialog");
    expect(dialog.getAttribute("aria-modal")).toBe("true");
    expect(screen.getByRole("heading", { name: "Add Task" })).toBeTruthy();
  });

  it("closes on Escape", () => {
    const { onClose } = setup(null);

    fireEvent.keyDown(window, { key: "Escape" });

    expect(onClose).toHaveBeenCalled();
  });

  it("requires a title", async () => {
    const { onSave } = setup(null);

    await save();

    expect(onSave).not.toHaveBeenCalled();
    expect(screen.getByText("Title is required.")).toBeTruthy();
  });

  it("shows the error when saving fails and stays open", async () => {
    const onSave = vi.fn().mockRejectedValue(new Error("Disk full"));
    const onClose = vi.fn();
    render(withAi(<TaskModal open initial={null} onClose={onClose} onSave={onSave} />));
    fireEvent.change(screen.getByLabelText("Title"), { target: { value: "x" } });

    await save();

    expect(screen.getByText("Disk full")).toBeTruthy();
    expect(onClose).not.toHaveBeenCalled();
  });

  it("parses tags from text with hashes, spaces and commas", async () => {
    const { onSave } = setup(null);
    fireEvent.change(screen.getByLabelText("Title"), { target: { value: "x" } });
    fireEvent.change(screen.getByLabelText("Tags"), { target: { value: "#work, home  #ideas" } });

    await save();

    expect(onSave.mock.calls[0][0].tags).toEqual(["work", "home", "ideas"]);
  });
});
