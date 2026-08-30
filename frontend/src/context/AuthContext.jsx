import {
  createContext,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";

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


  const login = (authToken, userData) => {
    setToken(authToken);
    setUser(userData);
  };


  const logout = () => {
    setToken(null);
    setUser(null);
  };


  const value = useMemo(
    () => ({
      token,
      user,
      isAuthenticated: Boolean(token),
      login,
      logout,
    }),
    [token, user]
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