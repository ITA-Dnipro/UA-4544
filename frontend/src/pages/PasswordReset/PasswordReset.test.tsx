import "@testing-library/jest-dom";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { BrowserRouter } from "react-router-dom";
import { vi, describe, test, expect, beforeEach } from "vitest";
import PasswordResetRequest from "./PasswordResetRequest";
import PasswordResetConfirm from "./PasswordResetConfirm";

const renderWithRouter = (ui: React.ReactElement) => {
  return render(<BrowserRouter>{ui}</BrowserRouter>);
};

describe("Password Reset Flow", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  test("shows success message after submitting email (even if API fails)", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() => Promise.reject(new Error("Network error"))),
    );

    renderWithRouter(<PasswordResetRequest />);

    const emailInput = screen.getByLabelText(/email address/i);

    fireEvent.change(emailInput, {
      target: { value: "test@example.com" },
    });

    fireEvent.submit(emailInput.closest("form")!);

    expect(await screen.findByText(/check your email/i)).toBeInTheDocument();
  });

  test("disables submit button when email is invalid", () => {
    renderWithRouter(<PasswordResetRequest />);

    const button = screen.getByRole("button", {
      name: /reset password/i,
    });

    expect(button).toBeDisabled();
  });

  test("validates password mismatch", async () => {
    window.history.pushState({}, "Test", "/reset-password?token=abc&uid=123");

    renderWithRouter(<PasswordResetConfirm />);

    const passwordInput = screen.getByPlaceholderText(/enter new password/i);
    const confirmInput = screen.getByPlaceholderText(/repeat password/i);

    fireEvent.change(passwordInput, {
      target: { value: "Password123" },
    });

    fireEvent.change(confirmInput, {
      target: { value: "Wrong123" },
    });

    expect(
      await screen.findByText(/passwords do not match/i),
    ).toBeInTheDocument();
  });

  test("submits successfully with valid token", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() =>
        Promise.resolve({
          ok: true,
          json: async () => ({ message: "success" }),
        }),
      ),
    );

    window.history.pushState({}, "Test", "/reset-password?token=abc&uid=123");

    renderWithRouter(<PasswordResetConfirm />);

    const passwordInput = screen.getByPlaceholderText(/enter new password/i);
    const confirmInput = screen.getByPlaceholderText(/repeat password/i);

    fireEvent.change(passwordInput, {
      target: { value: "Password123" },
    });

    fireEvent.change(confirmInput, {
      target: { value: "Password123" },
    });

    fireEvent.click(screen.getByRole("button", { name: /save password/i }));

    expect(await screen.findByText(/password changed/i)).toBeInTheDocument();
  });

  test("shows error for invalid or expired token", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() =>
        Promise.resolve({
          ok: false,
        }),
      ),
    );

    window.history.pushState({}, "Test", "/reset-password?token=bad&uid=123");

    renderWithRouter(<PasswordResetConfirm />);

    fireEvent.change(screen.getByPlaceholderText(/enter new password/i), {
      target: { value: "Password123" },
    });

    fireEvent.change(screen.getByPlaceholderText(/repeat password/i), {
      target: { value: "Password123" },
    });

    fireEvent.click(screen.getByRole("button", { name: /save password/i }));

    expect(
      await screen.findByText(/invalid or has expired/i),
    ).toBeInTheDocument();
  });

  test("shows error UI when token is missing", () => {
    window.history.pushState({}, "Test", "/reset-password");

    renderWithRouter(<PasswordResetConfirm />);

    expect(screen.getByText(/reset link error/i)).toBeInTheDocument();

    expect(screen.getByText(/invalid or has expired/i)).toBeInTheDocument();
  });
});
