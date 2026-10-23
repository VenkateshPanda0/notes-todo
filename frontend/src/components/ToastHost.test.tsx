import { act, fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { itemsApi } from "../api/client";
import { removeWithUndo } from "../lib/trash";
import { ToastHost } from "./ToastHost";

describe("delete with Undo", () => {
  it("offers Undo after a delete and restores the item", async () => {
    vi.spyOn(itemsApi, "remove").mockResolvedValue();
    const restore = vi.spyOn(itemsApi, "restore").mockResolvedValue({} as never);
    render(<ToastHost />);

    await act(async () => removeWithUndo({ id: 9, title: "Water plants" }));
    expect(screen.getByRole("status").textContent).toContain('Moved "Water plants" to Trash');

    fireEvent.click(screen.getByRole("button", { name: "Undo" }));
    expect(restore).toHaveBeenCalledWith(9);
    expect(screen.queryByRole("button", { name: "Undo" })).toBeNull();
  });
});
