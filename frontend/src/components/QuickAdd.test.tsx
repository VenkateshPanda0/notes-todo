import { act, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { itemsApi } from "../api/client";
import { makeItem } from "../test/fixtures";
import { QuickAdd } from "./QuickAdd";

const preview = {
  title: "call dentist",
  type: "TODO" as const,
  priority: "HIGH" as const,
  due_date: "2026-10-23",
  tags: ["errands"],
};

beforeEach(() => {
  vi.useFakeTimers();
});
afterEach(() => {
  vi.useRealTimers();
});

const input = () => screen.getByLabelText("Quick add") as HTMLInputElement;

async function typeAndSettle(text: string) {
  fireEvent.change(input(), { target: { value: text } });
  await act(async () => {
    await vi.advanceTimersByTimeAsync(250); // past the 200ms debounce
  });
}

describe("QuickAdd", () => {
  it("shows a live preview of how the text will be understood", async () => {
    const parse = vi.spyOn(itemsApi, "parse").mockResolvedValue(preview);
    render(<QuickAdd defaultType="TODO" onCreated={() => {}} />);

    await typeAndSettle("call dentist next friday !high #errands");

    expect(parse).toHaveBeenCalledWith("call dentist next friday !high #errands");
    expect(screen.getByText("call dentist")).toBeTruthy();
    expect(screen.getByText("High")).toBeTruthy();
    expect(screen.getByText("#errands")).toBeTruthy();
    expect(screen.getByText(/Due .*Oct/)).toBeTruthy();
  });

  it("debounces: rapid typing triggers one request", async () => {
    const parse = vi.spyOn(itemsApi, "parse").mockResolvedValue(preview);
    render(<QuickAdd defaultType="TODO" onCreated={() => {}} />);

    fireEvent.change(input(), { target: { value: "c" } });
    fireEvent.change(input(), { target: { value: "ca" } });
    fireEvent.change(input(), { target: { value: "cal" } });
    await act(async () => {
      await vi.advanceTimersByTimeAsync(250);
    });

    expect(parse).toHaveBeenCalledTimes(1);
  });

  it("creates the parsed item on Enter, reports it and clears the box", async () => {
    vi.spyOn(itemsApi, "parse").mockResolvedValue(preview);
    const create = vi.spyOn(itemsApi, "create").mockResolvedValue(makeItem({ id: 9, title: "call dentist" }));
    const onCreated = vi.fn();
    render(<QuickAdd defaultType="TODO" onCreated={onCreated} />);
    await typeAndSettle("call dentist next friday !high #errands");

    await act(async () => {
      fireEvent.keyDown(input(), { key: "Enter" });
    });

    expect(create).toHaveBeenCalledWith({
      title: "call dentist",
      type: "TODO",
      priority: "HIGH",
      due_date: "2026-10-23",
      tags: ["errands"],
    });
    expect(onCreated.mock.calls[0][0].id).toBe(9);
    expect(input().value).toBe("");
  });

  it("on the Notes view, plain text is sent as a note", async () => {
    const parse = vi.spyOn(itemsApi, "parse").mockResolvedValue({ ...preview, type: "NOTE" });
    render(<QuickAdd defaultType="NOTE" onCreated={() => {}} />);

    await typeAndSettle("wifi password");

    expect(parse).toHaveBeenCalledWith("note: wifi password");
  });

  it("doesn't add a second note: prefix when the user already typed one", async () => {
    const parse = vi.spyOn(itemsApi, "parse").mockResolvedValue({ ...preview, type: "NOTE" });
    render(<QuickAdd defaultType="NOTE" onCreated={() => {}} />);

    await typeAndSettle("Note: already prefixed");

    expect(parse).toHaveBeenCalledWith("Note: already prefixed");
  });

  it("ignores Enter on empty or whitespace-only input", async () => {
    const create = vi.spyOn(itemsApi, "create");
    render(<QuickAdd defaultType="TODO" onCreated={() => {}} />);

    await act(async () => {
      fireEvent.keyDown(input(), { key: "Enter" });
    });
    fireEvent.change(input(), { target: { value: "   " } });
    await act(async () => {
      fireEvent.keyDown(input(), { key: "Enter" });
    });

    expect(create).not.toHaveBeenCalled();
  });

  it("shows an error and keeps the text when saving fails", async () => {
    vi.spyOn(itemsApi, "parse").mockResolvedValue(preview);
    vi.spyOn(itemsApi, "create").mockRejectedValue(new Error("Server exploded"));
    render(<QuickAdd defaultType="TODO" onCreated={() => {}} />);
    await typeAndSettle("call dentist");

    await act(async () => {
      fireEvent.keyDown(input(), { key: "Enter" });
    });

    await act(async () => {
      await vi.advanceTimersByTimeAsync(0); // flush the rejected promise
    });
    expect(screen.getByText("Server exploded")).toBeTruthy();
    expect(input().value).toBe("call dentist");
  });

  it("Escape leaves the field", async () => {
    render(<QuickAdd defaultType="TODO" onCreated={() => {}} />);
    input().focus();
    expect(document.activeElement).toBe(input());

    fireEvent.keyDown(input(), { key: "Escape" });

    expect(document.activeElement).not.toBe(input());
  });
});
