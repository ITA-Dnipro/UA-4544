import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import "@testing-library/jest-dom";
import { BrowserRouter } from "react-router-dom";
import LoginPage from "./Login";
import React from "react";
import { describe, test, expect, vi } from "vitest";

const renderWithRouter = (ui: React.ReactElement) => {
  return render(<BrowserRouter>{ui}</BrowserRouter>);
};

describe("LoginPage", () => {
  test("renders all fields", () => {
    renderWithRouter(<LoginPage />);
    expect(screen.getByLabelText(/email address/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/^password$/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/user role/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/remember me/i)).toBeInTheDocument();
  });

  test("validation errors appear", async () => {
    renderWithRouter(<LoginPage />);
    fireEvent.click(screen.getByRole("button", { name: /log in/i }));
    expect(await screen.findByText(/email is required/i)).toBeInTheDocument();
    expect(
      await screen.findByText(/password is required/i),
    ).toBeInTheDocument();
  });

  test("email format validation", async () => {
    renderWithRouter(<LoginPage />);
    const emailInput = screen.getByLabelText(/email address/i);
    fireEvent.change(emailInput, { target: { value: "wrong-format" } });
    fireEvent.blur(emailInput);
    expect(
      await screen.findByText(/invalid email format/i),
    ).toBeInTheDocument();
  });

  test("toggle password visibility", async () => {
    renderWithRouter(<LoginPage />);

    const passwordInput = screen.getByLabelText(
      /^password$/i,
    ) as HTMLInputElement;
    const toggleButton = screen.getByRole("button", { name: /show password/i });

    expect(passwordInput.type).toBe("password");

    fireEvent.click(toggleButton);

    expect(passwordInput.type).toBe("text");
    expect(
      screen.getByRole("button", { name: /hide password/i }),
    ).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /hide password/i }));

    expect(passwordInput.type).toBe("password");
    expect(
      screen.getByRole("button", { name: /show password/i }),
    ).toBeInTheDocument();
  });

  test("role selection options", () => {
    renderWithRouter(<LoginPage />);
    expect(
      screen.getByRole("option", { name: /startup/i }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("option", { name: /investor/i }),
    ).toBeInTheDocument();
  });

  test("password minimum length validation", async () => {
    renderWithRouter(<LoginPage />);
    const passwordInput = screen.getByLabelText(/^password$/i);
    fireEvent.change(passwordInput, { target: { value: "abc" } });
    fireEvent.blur(passwordInput);
    expect(
      await screen.findByText(/minimum 6 characters required/i),
    ).toBeInTheDocument();
  });

  test("forgot password link renders and points to /password-reset", () => {
    renderWithRouter(<LoginPage />);
    const forgotLink = screen.getByRole("link", { name: /forgot password/i });
    expect(forgotLink).toBeInTheDocument();
    expect(forgotLink).toHaveAttribute("href", "/password-reset");
  });

  test("create account link renders and points to /register", () => {
    renderWithRouter(<LoginPage />);
    const registerLink = screen.getByRole("link", { name: /create an account/i });
    expect(registerLink).toBeInTheDocument();
    expect(registerLink).toHaveAttribute("href", "/register");
  });

  test("remember me checkbox is unchecked by default", () => {
    renderWithRouter(<LoginPage />);
    const checkbox = screen.getByLabelText(/remember me/i) as HTMLInputElement;
    expect(checkbox.checked).toBe(false);
  });

  test("remember me checkbox can be checked", () => {
    renderWithRouter(<LoginPage />);
    const checkbox = screen.getByLabelText(/remember me/i) as HTMLInputElement;
    fireEvent.click(checkbox);
    expect(checkbox.checked).toBe(true);
  });

  test("submit button is present and labeled Log In", () => {
    renderWithRouter(<LoginPage />);
    expect(
      screen.getByRole("button", { name: /log in/i }),
    ).toBeInTheDocument();
  });

  test("submit button becomes disabled while loading", async () => {
    vi.useFakeTimers();
    const { container } = renderWithRouter(<LoginPage />);

    fireEvent.change(screen.getByLabelText(/email address/i), {
      target: { value: "test@example.com" },
    });
    fireEvent.change(screen.getByLabelText(/^password$/i), {
      target: { value: "password123" },
    });

    const submitButton = container.querySelector(
      "button[type='submit']",
    ) as HTMLButtonElement;
    expect(submitButton).not.toBeDisabled();

    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(submitButton).toBeDisabled();
    });

    vi.useRealTimers();
  });

  test("role defaults to startup", () => {
    renderWithRouter(<LoginPage />);
    const roleSelect = screen.getByLabelText(/user role/i) as HTMLSelectElement;
    expect(roleSelect.value).toBe("startup");
  });

  test("role can be changed to investor", () => {
    renderWithRouter(<LoginPage />);
    const roleSelect = screen.getByLabelText(/user role/i) as HTMLSelectElement;
    fireEvent.change(roleSelect, { target: { value: "investor" } });
    expect(roleSelect.value).toBe("investor");
  });

  test("page heading renders", () => {
    renderWithRouter(<LoginPage />);
    expect(
      screen.getByRole("heading", { name: /login to platform/i }),
    ).toBeInTheDocument();
  });
});
