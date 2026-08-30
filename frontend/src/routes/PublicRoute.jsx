import { Navigate, Outlet } from "react-router-dom";
import { useAuthContext } from "../context/AuthContext";

function PublicRoute() {
  const { isAuthenticated, token } = useAuthContext();

  if (isAuthenticated && token) {
    return <Navigate to="/dashboard" replace />;
  }

  return <Outlet />;
}

export default PublicRoute;