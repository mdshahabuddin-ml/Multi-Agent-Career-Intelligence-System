import { Navigate, Outlet } from "react-router-dom";
import { useAuthContext } from "../context/AuthContext";
import Loading from "../components/common/Loading";

function PublicRoute() {
  const { isAuthenticated, token, authChecking } = useAuthContext();

  // Wait for session validation so a dead stored token doesn't bounce
  // a logged-out user to /dashboard (or vice versa).
  if (authChecking) {
    return <Loading />;
  }

  if (isAuthenticated && token) {
    return <Navigate to="/dashboard" replace />;
  }

  return <Outlet />;
}

export default PublicRoute;