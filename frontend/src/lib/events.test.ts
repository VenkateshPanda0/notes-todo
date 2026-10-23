import { describe, expect, it, vi } from "vitest";
import { itemsApi } from "../api/client";
import { notifyItemsChanged, onItemsChanged } from "./events";

describe("items-changed signal", () => {
  it("notifies every subscriber, and stops after unsubscribe", () => {
    const a = vi.fn();
    const b = vi.fn();
    const offA = onItemsChanged(a);
    onItemsChanged(b)();

    notifyItemsChanged();
    offA();
    notifyItemsChanged();

    expect(a).toHaveBeenCalledTimes(1);
    expect(b).not.toHaveBeenCalled();
  });
});

describe("API client writes announce themselves", () => {
  const respond = (status: number, body: unknown) =>
    vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(status === 204 ? null : JSON.stringify(body), { status }));

  it.each([
    ["create", () => itemsApi.create({ title: "x", type: "TODO" })],
    ["update", () => itemsApi.update(1, { title: "y" })],
    ["complete", () => itemsApi.complete(1)],
    ["reopen", () => itemsApi.reopen(1)],
    ["convert", () => itemsApi.convert(1)],
  ])("%s fires the signal after a successful write", async (_name, call) => {
    respond(200, { id: 1 });
    const heard = vi.fn();
    const off = onItemsChanged(heard);

    await call();
    off();

    expect(heard).toHaveBeenCalledTimes(1);
  });

  it("remove fires the signal too", async () => {
    respond(204, null);
    const heard = vi.fn();
    const off = onItemsChanged(heard);

    await itemsApi.remove(1);
    off();

    expect(heard).toHaveBeenCalledTimes(1);
  });

  it("does not fire when the write fails", async () => {
    respond(500, { detail: "boom" });
    const heard = vi.fn();
    const off = onItemsChanged(heard);

    await expect(itemsApi.create({ title: "x", type: "TODO" })).rejects.toThrow("boom");
    off();

    expect(heard).not.toHaveBeenCalled();
  });

  it("reads never fire it (so refreshing the badge cannot loop)", async () => {
    respond(200, []);
    const heard = vi.fn();
    const off = onItemsChanged(heard);

    await itemsApi.list();
    off();

    expect(heard).not.toHaveBeenCalled();
  });
});
