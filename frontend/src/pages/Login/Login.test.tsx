import { render, screen, fireEvent } from "@testing-library/react";
import "@testing-library/jest-dom";
import { BrowserRouter } from "react-router-dom";
import LoginPage from "./Login";
import React from "react";

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
});
