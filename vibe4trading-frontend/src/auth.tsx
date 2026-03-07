import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";
import { getApiBaseUrl } from "@/app/lib/v4t";

export type SessionUser = {
  authenticated: true;
  user_id: string;
  email: string | null;
  display_name: string | null;
  has_api_token: boolean;
  is_admin: boolean;
  quota: {
    runs_used: number;
    runs_limit: number;
    has_quota: boolean;
  };
};

type SessionData =
  | { authenticated: false }
  | SessionUser;

type AuthStatus = "loading" | "authenticated" | "unauthenticated";

type AuthContextType = {
  status: AuthStatus;
  user: SessionUser | null;
  signIn: (redirectTo?: string) => void;
  signOut: () => Promise<void>;
  refresh: () => Promise<void>;
};

const AuthContext = createContext<AuthContextType | null>(null);

export function useAuth(): AuthContextType {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be inside AuthProvider");
  return ctx;
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<AuthStatus>("loading");
  const [user, setUser] = useState<SessionUser | null>(null);

  const fetchSession = useCallback(async () => {
    try {
      const base = getApiBaseUrl();
      const res = await fetch(`${base}/auth/session`, {
        credentials: "include",
        cache: "no-store",
      });
      if (!res.ok) {
        setUser(null);
        setStatus("unauthenticated");
        return;
      }
      const data: SessionData = await res.json();
      if (data.authenticated) {
        setUser(data);
        setStatus("authenticated");
      } else {
        setUser(null);
        setStatus("unauthenticated");
      }
    } catch {
      setUser(null);
      setStatus("unauthenticated");
    }
  }, []);

  useEffect(() => {
    fetchSession();
  }, [fetchSession]);

  const signIn = useCallback((redirectTo?: string) => {
    const base = getApiBaseUrl();
    const params = redirectTo ? `?redirect_to=${encodeURIComponent(redirectTo)}` : "";
    window.location.href = `${base}/auth/login${params}`;
  }, []);

  const signOut = useCallback(async () => {
    try {
      const base = getApiBaseUrl();
      await fetch(`${base}/auth/logout`, {
        credentials: "include",
      });
    } catch {
      void 0;
    }
    setUser(null);
    setStatus("unauthenticated");
  }, []);

  return (
    <AuthContext.Provider
      value={{ status, user, signIn, signOut, refresh: fetchSession }}
    >
      {children}
    </AuthContext.Provider>
  );
}
