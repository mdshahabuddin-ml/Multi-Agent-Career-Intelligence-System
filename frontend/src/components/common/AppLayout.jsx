import { Outlet } from "react-router-dom";
import Navbar from "./Navbar";
import Sidebar from "./Sidebar";


function AppLayout() {
  return (
    <div className="app-layout">
      <Navbar />

      <div className="app-content">
        <Sidebar />

        <main className="main-content">
          <Outlet />
        </main>
      </div>
    </div>
  );
}


export default AppLayout;