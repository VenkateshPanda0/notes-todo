import { act, fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { authApi } from "../api/client";
import type { EncryptionResult, LockStatus } from "../api/client";
import { LockProvider } from "../contexts/LockContext";
import { EncryptionSettings } from "./EncryptionSettings";

async function setup(status: Partial<LockStatus> = {}) {
  const full: LockStatus = { is_locked: true, encrypted: false, encryption_available: true, ...status };
  const statusSpy = vi.spyOn(authApi, "status").mockResolvedValue(full);
  render(
    <LockProvider>
      <EncryptionSettings />
    </LockProvider>,
  );
  await act(async () => {}); // let LockProvider load the status
  return { statusSpy };
}

const open = async () => {
  fireEvent.click(screen.getByRole("button", { name: "Encrypt database…" }));
};
const passwordBox = () => screen.getByLabelText("Confirm your app password") as HTMLInputElement;
const encryptButton = () => screen.getByRole("button", { name: /Encrypt now|Encrypting…/ }) as HTMLButtonElement;
const type = (value: string) => fireEvent.change(passwordBox(), { target: { value } });

beforeEach(() => {
  vi.spyOn(authApi, "lock").mockResolvedValue(undefined);
});

describe("EncryptionSettings visibility", () => {
  it("renders nothing until an app password exists (it is the encryption key)", async () => {
    await setup({ is_locked: false });

    expect(screen.queryByText("Database encryption")).toBeNull();
  });

  it("explains when this build can't encrypt", async () => {
    await setup({ encryption_available: false });

    expect(screen.getByText(/isn't available in this build/)).toBeTruthy();
    expect(screen.queryByRole("button", { name: "Encrypt database…" })).toBeNull();
  });

  it("describes the current state", async () => {
    await setup({ encrypted: false });
    expect(screen.getByText(/the data file itself is readable/)).toBeTruthy();
  });

  it("offers removal when already encrypted", async () => {
    await setup({ encrypted: true });

    expect(screen.getByText(/Your data file is encrypted \(AES-256\)/)).toBeTruthy();
    expect(screen.getByRole("button", { name: "Remove encryption…" })).toBeTruthy();
    expect(screen.queryByRole("button", { name: "Encrypt database…" })).toBeNull();
  });
});

describe("turning encryption on", () => {
  it("warns plainly that a forgotten password means lost data", async () => {
    await setup();
    await open();

    expect(screen.getByText(/If you forget your password, your notes cannot be recovered/)).toBeTruthy();
    expect(screen.getByRole("group", { name: "Encrypt database" })).toBeTruthy();
  });

  it("stays disabled until the password is long enough AND the risk is acknowledged", async () => {
    await setup();
    await open();
    expect(encryptButton().disabled).toBe(true);

    type("abc");
    fireEvent.click(screen.getByLabelText(/I understand/));
    expect(encryptButton().disabled).toBe(true); // too short

    type("abcd");
    expect(encryptButton().disabled).toBe(false);

    fireEvent.click(screen.getByLabelText(/I understand/)); // un-acknowledge
    expect(encryptButton().disabled).toBe(true);
  });

  it("calls the API with the password, reports the result and refreshes the status", async () => {
    const enable = vi
      .spyOn(authApi, "enableEncryption")
      .mockResolvedValue({ encrypted: true, removed_plain_backups: 3 } satisfies EncryptionResult);
    const { statusSpy } = await setup();
    await open();
    type("correct horse");
    fireEvent.click(screen.getByLabelText(/I understand/));
    const callsBefore = statusSpy.mock.calls.length;

    await act(async () => {
      fireEvent.click(encryptButton());
    });

    expect(enable).toHaveBeenCalledExactlyOnceWith("correct horse");
    expect(screen.getByText(/Your database is now encrypted\. 3 older unencrypted backups were securely deleted/)).toBeTruthy();
    expect(statusSpy.mock.calls.length).toBeGreaterThan(callsBefore);
    expect(screen.queryByRole("group", { name: "Encrypt database" })).toBeNull(); // panel closed
  });

  it("uses singular wording for one backup and omits it for none", async () => {
    const enable = vi.spyOn(authApi, "enableEncryption");
    await setup();

    enable.mockResolvedValueOnce({ encrypted: true, removed_plain_backups: 1 });
    await open();
    type("correct horse");
    fireEvent.click(screen.getByLabelText(/I understand/));
    await act(async () => {
      fireEvent.click(encryptButton());
    });
    expect(screen.getByText(/1 older unencrypted backup was securely deleted/)).toBeTruthy();

    enable.mockResolvedValueOnce({ encrypted: true, removed_plain_backups: 0 });
    await open();
    type("correct horse");
    fireEvent.click(screen.getByLabelText(/I understand/));
    await act(async () => {
      fireEvent.click(encryptButton());
    });
    expect(screen.queryByText(/older unencrypted backup/)).toBeNull();
    expect(screen.getByText("Your database is now encrypted.")).toBeTruthy();
  });

  it("shows the server's reason and keeps the form open when it fails", async () => {
    vi.spyOn(authApi, "enableEncryption").mockRejectedValue(new Error("Incorrect password"));
    await setup();
    await open();
    type("wrong-one");
    fireEvent.click(screen.getByLabelText(/I understand/));

    await act(async () => {
      fireEvent.click(encryptButton());
    });

    expect(screen.getByText("Incorrect password")).toBeTruthy();
    expect(screen.getByRole("group", { name: "Encrypt database" })).toBeTruthy();
    expect(passwordBox().value).toBe("wrong-one");
  });

  it("disables the button and says so while working", async () => {
    let finish!: (r: EncryptionResult) => void;
    vi.spyOn(authApi, "enableEncryption").mockReturnValue(new Promise((resolve) => (finish = resolve)));
    await setup();
    await open();
    type("correct horse");
    fireEvent.click(screen.getByLabelText(/I understand/));

    await act(async () => {
      fireEvent.click(encryptButton());
    });
    expect(screen.getByRole("button", { name: "Encrypting…" }).hasAttribute("disabled")).toBe(true);
    expect(screen.getByRole("button", { name: "Cancel" }).hasAttribute("disabled")).toBe(true); // can't bail out mid-way

    await act(async () => finish({ encrypted: true, removed_plain_backups: 0 }));
  });

  it("cancel closes the panel and forgets the typed password and acknowledgement", async () => {
    await setup();
    await open();
    type("secret-secret");
    fireEvent.click(screen.getByLabelText(/I understand/));

    fireEvent.click(screen.getByRole("button", { name: "Cancel" }));
    await open();

    expect(passwordBox().value).toBe("");
    expect((screen.getByLabelText(/I understand/) as HTMLInputElement).checked).toBe(false);
  });
});

describe("turning encryption off", () => {
  it("needs only the password and reports success", async () => {
    const disable = vi.spyOn(authApi, "disableEncryption").mockResolvedValue({ encrypted: false, removed_plain_backups: 0 });
    await setup({ encrypted: true });

    fireEvent.click(screen.getByRole("button", { name: "Remove encryption…" }));
    const submit = screen.getByRole("button", { name: "Remove encryption" }) as HTMLButtonElement;
    expect(submit.disabled).toBe(true);
    type("correct horse");
    expect(submit.disabled).toBe(false);
    await act(async () => {
      fireEvent.click(submit);
    });

    expect(disable).toHaveBeenCalledExactlyOnceWith("correct horse");
    expect(screen.getByText(/Encryption removed/)).toBeTruthy();
  });

  it("shows an error when the password is wrong", async () => {
    vi.spyOn(authApi, "disableEncryption").mockRejectedValue(new Error("Incorrect password"));
    await setup({ encrypted: true });
    fireEvent.click(screen.getByRole("button", { name: "Remove encryption…" }));
    type("nope-nope");

    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: "Remove encryption" }));
    });

    expect(screen.getByText("Incorrect password")).toBeTruthy();
  });
});

describe("status refreshes", () => {
  it("keeps the success message visible after the status is re-checked", async () => {
    vi.spyOn(authApi, "enableEncryption").mockResolvedValue({ encrypted: true, removed_plain_backups: 0 });
    await setup();
    await open();
    type("correct horse");
    fireEvent.click(screen.getByLabelText(/I understand/));

    await act(async () => {
      fireEvent.click(encryptButton());
    });
    await act(async () => {}); // let the refresh settle

    expect(screen.getByText("Your database is now encrypted.")).toBeTruthy();
  });
});
