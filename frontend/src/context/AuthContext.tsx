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

interface AuthContextType {
  user: User | null;
  accessToken: string | null;
  login: (accessToken: string, refreshToken: string, user: User) => void;
  logout: () => void;
}

export const AuthContext = createContext<AuthContextType | null>(null);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({
  children,
}) => {
  const [user, setUser] = useState<User | null>(null);
  const [accessToken, setAccessToken] = useState<string | null>(null);
  const refreshTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const logout = useCallback(async () => {
    const refresh = localStorage.getItem("refresh_token");
    if (refresh) {
      await fetch("/api/auth/logout/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh }),
      }).catch(() => {});
    }
    setUser(null);
    setAccessToken(null);
    localStorage.removeItem("refresh_token");
    if (refreshTimerRef.current) clearTimeout(refreshTimerRef.current);
  }, []);

  const scheduleRefresh = useCallback(
    (refreshToken: string, token: string) => {
      if (refreshTimerRef.current) clearTimeout(refreshTimerRef.current);

      try {
        const payload = JSON.parse(atob(token.split(".")[1]));
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
    (access: string, refresh: string, userData: User) => {
      setAccessToken(access);
      setUser(userData);
      localStorage.setItem("refresh_token", refresh);
      scheduleRefresh(refresh, access);
    },
    [scheduleRefresh],
  );

  useEffect(() => {
    const refresh = localStorage.getItem("refresh_token");
    if (!refresh) return;

    fetch("/api/auth/refresh/", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh }),
    })
      .then((res) => (res.ok ? res.json() : Promise.reject()))
      .then((data) => {
        setAccessToken(data.access);
        const payload = JSON.parse(atob(data.access.split(".")[1]));
        setUser({
          id: payload.user_id,
          email: payload.email,
          role: payload.role,
        });
        scheduleRefresh(refresh, data.access);
      })
      .catch(logout);
  }, [logout, scheduleRefresh]);

  return (
    <AuthContext.Provider value={{ user, accessToken, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
};
