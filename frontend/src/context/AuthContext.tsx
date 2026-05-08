import React, {
  createContext,
  useState,
  useEffect,
  useRef,
  useCallback,
} from "react";

interface User {
  id: number;
  email: string;
  role: string;
}

const decodeJWT = (token: string) => {
  try {
    const base64Url = token.split(".")[1];
    const base64 = base64Url.replace(/-/g, "+").replace(/_/g, "/");
    const pad = base64.length % 4;
    const paddedBase64 = pad ? base64 + "=".repeat(4 - pad) : base64;

    return JSON.parse(
      decodeURIComponent(
        atob(paddedBase64)
          .split("")
          .map((c) => "%" + ("00" + c.charCodeAt(0).toString(16)).slice(-2))
          .join(""),
      ),
    );
  } catch (error) {
    console.error("JWT Decode Error:", error);
    return null;
  }
};

interface AuthContextType {
  user: User | null;
  accessToken: string | null;
  isLoading: boolean;
  login: (
    accessToken: string,
    refreshToken: string,
    user: User,
    remember: boolean,
  ) => void;
  logout: () => void;
}

export const AuthContext = createContext<AuthContextType | null>(null);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({
  children,
}) => {
  const [user, setUser] = useState<User | null>(null);
  const [accessToken, setAccessToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const refreshTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const logout = useCallback(async () => {
    const refresh =
      localStorage.getItem("refresh_token") ||
      sessionStorage.getItem("refresh_token");
    if (refreshTimerRef.current) clearTimeout(refreshTimerRef.current);
    setUser(null);
    setAccessToken(null);
    localStorage.removeItem("refresh_token");
    sessionStorage.removeItem("refresh_token");
    if (refresh) {
      await fetch("/api/auth/logout/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh }),
      }).catch(() => {});
    }
  }, []);

  const scheduleRefresh = useCallback(
    (refreshToken: string, token: string) => {
      if (refreshTimerRef.current) clearTimeout(refreshTimerRef.current);

      const payload = decodeJWT(token);
      if (!payload) {
        logout();
        return;
      }

      try {
        const expiresAt = payload.exp * 1000;
        const now = Date.now();

        const refreshIn = expiresAt - now - 2 * 60 * 1000;

        refreshTimerRef.current = setTimeout(
          async () => {
            try {
              const res = await fetch("/api/auth/refresh/", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ refresh: refreshToken }),
              });

              if (!res.ok) throw new Error();

              const data = await res.json();
              setAccessToken(data.access);

              scheduleRefresh(refreshToken, data.access);
            } catch {
              logout();
            }
          },
          Math.max(refreshIn, 0),
        );
      } catch {
        logout();
      }
    },
    [logout],
  );

  const login = useCallback(
    (access: string, refresh: string, userData: User, remember: boolean) => {
      setAccessToken(access);
      setUser(userData);
      if (remember) {
        localStorage.setItem("refresh_token", refresh);
      } else {
        sessionStorage.setItem("refresh_token", refresh);
      }
      scheduleRefresh(refresh, access);
    },
    [scheduleRefresh],
  );

  useEffect(() => {
    const refresh =
      localStorage.getItem("refresh_token") ||
      sessionStorage.getItem("refresh_token");
    if (!refresh) {
      setIsLoading(false);
      return;
    }

    fetch("/api/auth/refresh/", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh }),
    })
      .then((res) => (res.ok ? res.json() : Promise.reject()))
      .then((data) => {
        setAccessToken(data.access);
        const payload = decodeJWT(data.access);
        if (payload) {
          setUser({
            id: payload.user_id,
            email: payload.email,
            role: payload.role,
          });
          scheduleRefresh(refresh, data.access);
        } else {
          logout();
        }
      })
      .catch(logout)
      .finally(() => {
        setIsLoading(false);
      });
  }, [logout, scheduleRefresh]);

  return (
    <AuthContext.Provider
      value={{ user, accessToken, login, logout, isLoading }}
    >
      {isLoading ? (
        <div className="flex h-screen items-center justify-center">
          Loading...
        </div>
      ) : (
        children
      )}
    </AuthContext.Provider>
  );
};
