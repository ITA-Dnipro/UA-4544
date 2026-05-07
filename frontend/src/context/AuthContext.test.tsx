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

const TestComponent = () => {
  const auth = useContext(AuthContext);
  return (
    <div>
      <button
        onClick={() =>
          auth?.login(createMockToken(15), "refresh-123", {
            id: 1,
            email: "test@test.com",
            role: "startup",
          })
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
    fetchMock.mockResolvedValue({
      ok: true,
      json: async () => ({ access: createMockToken(15) }),
    } as Response);
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("should login and schedule refresh", async () => {
    render(
      <AuthProvider>
        <TestComponent />
      </AuthProvider>,
    );

    await act(async () => {
      screen.getByText("Login").click();
    });

    expect(localStorage.getItem("refresh_token")).toBe("refresh-123");

    await act(async () => {
      vi.runOnlyPendingTimers();
    });

    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/refresh/"),
      expect.any(Object),
    );
  });

  it("should logout when refresh fails", async () => {
    render(
      <AuthProvider>
        <TestComponent />
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
  });
});
