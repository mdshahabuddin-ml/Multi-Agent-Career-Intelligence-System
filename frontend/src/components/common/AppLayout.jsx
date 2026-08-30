import Navbar from "./Navbar";
import Sidebar from "./Sidebar";


function AppLayout({
  children,
}) {
  return (
    <div className="app-layout">
      <Navbar />

      <div className="app-content">
        <Sidebar />

        <main className="main-content">
          {children}
        </main>
      </div>
    </div>
  );
}


export default AppLayout;