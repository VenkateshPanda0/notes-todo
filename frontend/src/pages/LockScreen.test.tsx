import { act, fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { authApi } from "../api/client";
import type { LockStatus } from "../api/client";
import { LockProvider } from "../contexts/LockContext";
import { LockScreen } from "./LockScreen";

async function setup(status: Partial<LockStatus>) {
  vi.spyOn(authApi, "status").mockResolvedValue({
    is_locked: true,
    encrypted: false,
    encryption_available: true,
    ...status,
  });
  render(
    <LockProvider>
      <LockScreen />
    </LockProvider>,
  );
  await act(async () => {});
}

const submit = async (password: string) => {
  fireEvent.change(screen.getByLabelText("Password"), { target: { value: password } });
  await act(async () => {
    fireEvent.keyDown(screen.getByLabelText("Password"), { key: "Enter" });
  });
};

describe("LockScreen", () => {
  it("tells people their data is encrypted when it is", async () => {
    await setup({ encrypted: true });

    expect(screen.getByText("Your data is encrypted. Enter your password to unlock it.")).toBeTruthy();
    expect(screen.getByRole("button", { name: "Unlock" })).toBeTruthy();
  });

  it("uses the ordinary wording for an unencrypted lock", async () => {
    await setup({ encrypted: false });

    expect(screen.getByText("Enter your password to continue.")).toBeTruthy();
    expect(screen.getByRole("button", { name: "Sign In" })).toBeTruthy();
  });

  it("shows the server's actual reason when unlocking fails", async () => {
    await setup({ encrypted: true });
    vi.spyOn(authApi, "unlock").mockRejectedValue(new Error("Too many failed attempts. Try again in 30 seconds."));

    await submit("whatever");

    expect(screen.getByText("Too many failed attempts. Try again in 30 seconds.")).toBeTruthy();
  });

  it("shows 'Incorrect password' for a wrong password", async () => {
    await setup({ encrypted: true });
    vi.spyOn(authApi, "unlock").mockRejectedValue(new Error("Incorrect password"));

    await submit("wrong");

    expect(screen.getByText("Incorrect password")).toBeTruthy();
  });

  it("shows the first-run setup when no password exists yet", async () => {
    await setup({ is_locked: false });

    expect(screen.getByText("Set an app password")).toBeTruthy();
    expect(screen.getByLabelText("Confirm password")).toBeTruthy();
  });
});
