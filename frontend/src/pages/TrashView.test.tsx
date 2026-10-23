import { act, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { itemsApi } from "../api/client";
import { makeItem } from "../test/fixtures";
import { TrashView } from "./TrashView";

afterEach(() => vi.restoreAllMocks());

const ago = (days: number) => new Date(Date.now() - days * 86_400_000).toISOString();

async function renderTrash(items: ReturnType<typeof makeItem>[]) {
  const list = vi.spyOn(itemsApi, "listTrash").mockResolvedValue(items);
  render(<TrashView />);
  await act(async () => {});
  return list;
}

describe("Trash", () => {
  it("shows an empty state", async () => {
    await renderTrash([]);
    expect(screen.getByText("The Trash is empty.")).toBeTruthy();
    expect(screen.queryByRole("button", { name: "Empty Trash" })).toBeNull();
  });

  it("shows how long each item has left", async () => {
    await renderTrash([makeItem({ id: 1, title: "Old thing", deleted_at: ago(10) })]);
    expect(screen.getByText(/20 days left/)).toBeTruthy();
  });

  it("restores an item", async () => {
    const restore = vi.spyOn(itemsApi, "restore").mockResolvedValue(makeItem({ id: 1 }));
    await renderTrash([makeItem({ id: 1, title: "Old thing", deleted_at: ago(1) })]);
    fireEvent.click(screen.getByRole("button", { name: "Restore" }));
    expect(restore).toHaveBeenCalledWith(1);
  });

  it("deletes one item forever", async () => {
    const purge = vi.spyOn(itemsApi, "purge").mockResolvedValue();
    await renderTrash([makeItem({ id: 4, title: "Old thing", deleted_at: ago(1) })]);
    fireEvent.click(screen.getByRole("button", { name: 'Delete "Old thing" forever' }));
    expect(purge).toHaveBeenCalledWith(4);
  });

  it("asks before emptying the Trash", async () => {
    const empty = vi.spyOn(itemsApi, "emptyTrash").mockResolvedValue({ deleted: 1 });
    await renderTrash([makeItem({ id: 1, deleted_at: ago(1) })]);
    fireEvent.click(screen.getByRole("button", { name: "Empty Trash" }));
    expect(empty).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", { name: "Cancel" }));
    expect(empty).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", { name: "Empty Trash" }));
    fireEvent.click(screen.getByRole("button", { name: "Delete all" }));
    expect(empty).toHaveBeenCalledTimes(1);
  });
});
