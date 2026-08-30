import { useAuthContext } from "../../context/AuthContext";
import { useAppContext } from "../../context/AppContext";


function Navbar() {
  const { user, logout } =
    useAuthContext();

  const {
    setSidebarOpen,
  } = useAppContext();


  return (
    <header className="navbar">
      <button
        className="menu-button"
        onClick={() =>
          setSidebarOpen(
            (previous) => !previous
          )
        }
      >
        ☰
      </button>


      <div className="navbar-brand">
        <strong>
          CareerIntel AI
        </strong>
      </div>


      <div className="navbar-user">
        <span>
          {user?.full_name ||
            "Candidate"}
        </span>

        <button
          onClick={logout}
          className="logout-button"
        >
          Logout
        </button>
      </div>
    </header>
  );
}


export default Navbar;