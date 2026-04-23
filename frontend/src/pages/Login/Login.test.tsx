import { render, screen, fireEvent } from "@testing-library/react";
import "@testing-library/jest-dom";
import LoginPage from "./Login";

describe("LoginPage", () => {
  test("renders all fields", () => {
    render(<LoginPage />);
    expect(screen.getByLabelText(/електронна пошта/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/пароль/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/роль користувача/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/запам'ятати мене/i)).toBeInTheDocument();
  });

  test("validation errors appear", async () => {
    render(<LoginPage />);
    fireEvent.click(screen.getByRole("button", { name: /увійти/i }));
    expect(await screen.findByText(/обов'язкове поле/i)).toBeInTheDocument();
    expect(await screen.findByText(/пароль обов'язковий/i)).toBeInTheDocument();
  });

  test("email format validation", async () => {
    render(<LoginPage />);
    const emailInput = screen.getByLabelText(/електронна пошта/i);
    fireEvent.change(emailInput, { target: { value: "wrong" } });
    fireEvent.blur(emailInput);
    expect(await screen.findByText(/невірний формат/i)).toBeInTheDocument();
  });

  test("toggle password visibility", () => {
    render(<LoginPage />);
    const passwordInput = screen.getByLabelText(/пароль/i) as HTMLInputElement;
    const toggleButton = screen.getByRole("button", { name: "" });
    expect(passwordInput.type).toBe("password");
    fireEvent.click(toggleButton);
    expect(passwordInput.type).toBe("text");
  });
});
