import { render, screen, fireEvent } from "@testing-library/react";
import "@testing-library/jest-dom";
import { BrowserRouter } from "react-router-dom";
import LoginPage from "./Login";

const renderWithRouter = (ui: React.ReactElement) => {
  return render(<BrowserRouter>{ui}</BrowserRouter>);
};

describe("LoginPage", () => {
  test("renders all fields", () => {
    renderWithRouter(<LoginPage />);
    expect(screen.getByLabelText(/електронна пошта/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/пароль/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/роль/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/запам'ятати мене/i)).toBeInTheDocument();
  });

  test("validation errors appear", async () => {
    renderWithRouter(<LoginPage />);
    fireEvent.click(screen.getByRole("button", { name: /увійти/i }));
    expect(await screen.findByText(/обов'язкове поле/i)).toBeInTheDocument();
  });

  test("email format validation", async () => {
    renderWithRouter(<LoginPage />);
    const emailInput = screen.getByLabelText(/електронна пошта/i);
    fireEvent.change(emailInput, { target: { value: "wrong" } });
    fireEvent.blur(emailInput);
    expect(await screen.findByText(/невірний формат/i)).toBeInTheDocument();
  });

  test("toggle password visibility", () => {
    renderWithRouter(<LoginPage />);
    const passwordInput = screen.getByPlaceholderText(
      /введіть пароль/i,
    ) as HTMLInputElement;
    const toggleButton = screen.getByRole("button", { name: "" });

    expect(passwordInput.type).toBe("password");
    fireEvent.click(toggleButton);
    expect(passwordInput.type).toBe("text");
  });

  test("role selection options", () => {
    renderWithRouter(<LoginPage />);
    expect(
      screen.getByRole("option", { name: /стартап/i }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("option", { name: /інвестор/i }),
    ).toBeInTheDocument();
  });
});
