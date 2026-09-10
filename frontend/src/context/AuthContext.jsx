import {
  createContext,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";
import { clearApiCache } from "../services/api";
import authService from "../services/authService";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [token, setToken] = useState(
    () =>
      localStorage.getItem(
        "careerintel_token"
      )
  );

  const [user, setUser] = useState(() => {
    const storedUser =
      localStorage.getItem(
        "careerintel_user"
      );

    return storedUser
      ? JSON.parse(storedUser)
      : null;
  });

  // True while we verify a restored token against the backend on app
  // load. Prevents rendering protected pages with a dead (expired or
  // stale-key) JWT that would fail every API call.
  const [authChecking, setAuthChecking] = useState(() =>
    Boolean(localStorage.getItem("careerintel_token"))
  );


  useEffect(() => {
    if (token) {
      localStorage.setItem(
        "careerintel_token",
        token
      );
    } else {
      localStorage.removeItem(
        "careerintel_token"
      );
    }
  }, [token]);


  useEffect(() => {
    if (user) {
      localStorage.setItem(
        "careerintel_user",
        JSON.stringify(user)
      );
    } else {
      localStorage.removeItem(
        "careerintel_user"
      );
    }
  }, [user]);

  // Validate any restored session once on app load.
  useEffect(() => {
    let cancelled = false;

    async function validateStoredSession() {
      const storedToken = localStorage.getItem("careerintel_token");
      if (!storedToken) {
        setAuthChecking(false);
        return;
      }

      try {
        const freshUser = await authService.getCurrentUserFresh();
        if (!cancelled) {
          setUser(freshUser);
        }
      } catch (err) {
        // Only drop the session when the backend positively rejects
        // the token (401). Network errors leave the session intact so
        // a down backend doesn't log the user out.
        if (!cancelled && err.response?.status === 401) {
          localStorage.removeItem("careerintel_token");
          localStorage.removeItem("careerintel_user");
          clearApiCache();
          setToken(null);
          setUser(null);
        }
      } finally {
        if (!cancelled) {
          setAuthChecking(false);
        }
      }
    }

    validateStoredSession();
    return () => {
      cancelled = true;
    };
  }, []);


  const login = (authToken, userData) => {
    // Store synchronously so localStorage is populated BEFORE any
    // navigation or component mount can fire API requests via api.js.
    localStorage.setItem("careerintel_token", authToken);
    localStorage.setItem("careerintel_user", JSON.stringify(userData));
    setToken(authToken);
    setUser(userData);
  };


  const logout = () => {
    localStorage.removeItem("careerintel_token");
    localStorage.removeItem("careerintel_user");
    clearApiCache();
    setToken(null);
    setUser(null);
  };


  const value = useMemo(
    () => ({
      token,
      user,
      isAuthenticated: Boolean(token),
      authChecking,
      login,
      logout,
    }),
    [token, user, authChecking]
  );


  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
}


export function useAuthContext() {
  const context =
    useContext(AuthContext);

  if (!context) {
    throw new Error(
      "useAuthContext must be used inside AuthProvider"
    );
  }

  return context;
}