import {
  Navigate,
  Route,
  Routes,
} from "react-router-dom";

import Login from "../pages/Login";
import Register from "../pages/Register";

import Dashboard from "../pages/Dashboard";
import Profile from "../pages/Profile";
import Resume from "../pages/Resume";
import Jobs from "../pages/Jobs";
import JobDetails from "../pages/JobDetails";
import Research from "../pages/Research";
import ResearchReport from "../pages/ResearchReport";
import Career from "../pages/Career";
import Interview from "../pages/Interview";
import Applications from "../pages/Applications";

import AppLayout from "../components/common/AppLayout";

import ProtectedRoute from "./ProtectedRoute";
import PublicRoute from "./PublicRoute";


function AppRoutes() {
  return (
    <Routes>

      {/* ==========================
          Public Routes
      ========================== */}

      <Route element={<PublicRoute />}>

        <Route
          path="/login"
          element={<Login />}
        />

        <Route
          path="/register"
          element={<Register />}
        />

      </Route>


      {/* ==========================
          Protected Routes
      ========================== */}

      <Route element={<ProtectedRoute />}>

        <Route
          element={<AppLayout />}
        >

          <Route
            path="/dashboard"
            element={<Dashboard />}
          />

          <Route
            path="/profile"
            element={<Profile />}
          />

          <Route
            path="/resume"
            element={<Resume />}
          />

          <Route
            path="/jobs"
            element={<Jobs />}
          />

          <Route
            path="/jobs/:jobId"
            element={<JobDetails />}
          />

          <Route
            path="/research"
            element={<Research />}
          />

          <Route
            path="/research/:researchId"
            element={<ResearchReport />}
          />

          <Route
            path="/career"
            element={<Career />}
          />

          <Route
            path="/interview"
            element={<Interview />}
          />

          <Route
            path="/applications"
            element={<Applications />}
          />

        </Route>

      </Route>


      {/* ==========================
          Default Route
      ========================== */}

      <Route
        path="*"
        element={
          <Navigate
            to="/dashboard"
            replace
          />
        }
      />

    </Routes>
  );
}


export default AppRoutes;