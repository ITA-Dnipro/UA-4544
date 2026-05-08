import { render, act, screen } from "@testing-library/react";
import { AuthProvider, AuthContext } from "./AuthContext";
import React, { useContext } from "react";
import {
  describe,
  it,
  expect,
  vi,
  beforeEach,
  afterEach,
  type Mock,
} from "vitest";

global.fetch = vi.fn();
const fetchMock = global.fetch as Mock;

const createMockToken = (expiresInMinutes: number) => {
  const payload = btoa(
    JSON.stringify({
      exp: Math.floor(Date.now() / 1000) + expiresInMinutes * 60,
      user_id: 1,
      email: "test@test.com",
      role: "startup",
    }),
  );
  return `header.${payload}.signature`;
};

const TestComponent = ({ remember = true }: { remember?: boolean }) => {
  const auth = useContext(AuthContext);
  return (
    <div>
      <button
        onClick={() =>
          auth?.login(
            createMockToken(15),
            "refresh-123",
            { id: 1, email: "test@test.com", role: "startup" },
            remember,
          )
        }
      >
        Login
      </button>
    </div>
  );
};

describe("AuthProvider Logic", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.clearAllMocks();
    localStorage.clear();
    sessionStorage.clear();
    fetchMock.mockResolvedValue({
      ok: true,
      json: async () => ({ access: createMockToken(15) }),
    } as Response);
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("should store token in localStorage when remember is true", async () => {
    render(
      <AuthProvider>
        <TestComponent remember={true} />
      </AuthProvider>,
    );

    await act(async () => {
      screen.getByText("Login").click();
    });

    expect(localStorage.getItem("refresh_token")).toBe("refresh-123");
    expect(sessionStorage.getItem("refresh_token")).toBeNull();
  });

  it("should store token in sessionStorage when remember is false", async () => {
    render(
      <AuthProvider>
        <TestComponent remember={false} />
      </AuthProvider>,
    );

    await act(async () => {
      screen.getByText("Login").click();
    });

    expect(sessionStorage.getItem("refresh_token")).toBe("refresh-123");
    expect(localStorage.getItem("refresh_token")).toBeNull();
  });

  it("should logout and clear both storages when refresh fails", async () => {
    render(
      <AuthProvider>
        <TestComponent remember={true} />
      </AuthProvider>,
    );

    await act(async () => {
      screen.getByText("Login").click();
    });

    fetchMock.mockResolvedValueOnce({ ok: false } as Response);

    await act(async () => {
      vi.runOnlyPendingTimers();
    });

    expect(localStorage.getItem("refresh_token")).toBeNull();
    expect(sessionStorage.getItem("refresh_token")).toBeNull();
  });
});
