import { Navigate, Outlet } from "react-router-dom";
import { useAuthContext } from "../context/AuthContext";
import Loading from "../components/common/Loading";

function ProtectedRoute() {
  const { isAuthenticated, token, authChecking } = useAuthContext();

  // While the restored token is being validated, don't render protected
  // pages (their API calls would fail with a dead token).
  if (authChecking) {
    return <Loading />;
  }

  if (!isAuthenticated || !token) {
    return <Navigate to="/login" replace />;
  }

  return <Outlet />;
}

export default ProtectedRoute;