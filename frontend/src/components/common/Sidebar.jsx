import {
  NavLink,
} from "react-router-dom";

import { useAppContext } from "../../context/AppContext";


function Sidebar() {
  const {
    sidebarOpen,
  } = useAppContext();


  if (!sidebarOpen) {
    return null;
  }


  const links = [
    {
      label: "Dashboard",
      path: "/dashboard",
    },
    {
      label: "Profile",
      path: "/profile",
    },
    {
      label: "Resume",
      path: "/resume",
    },
    {
      label: "Jobs",
      path: "/jobs",
    },
    {
      label: "Research",
      path: "/research",
    },
    {
      label: "Career",
      path: "/career",
    },
    {
      label: "Interview",
      path: "/interview",
    },
    {
      label: "Applications",
      path: "/applications",
    },
    {
      label: "Hermes Agent",
      path: "/hermes",
    },
    {
      label: "Automations",
      path: "/automations",
    },
    {
      label: "Agent Memory",
      path: "/agent-memory",
    },
    {
      label: "Agent Skills",
      path: "/agent-skills",
    },
    {
      label: "Content",
      path: "/content",
    },
    {
      label: "Social Media",
      path: "/social",
    },
    {
      label: "Content Analytics",
      path: "/content-analytics",
    },
  ];


  return (
    <aside className="sidebar">
      <nav>
        {links.map((link) => (
          <NavLink
            key={link.path}
            to={link.path}
            className={({ isActive }) =>
              isActive
                ? "nav-link active"
                : "nav-link"
            }
          >
            {link.label}
          </NavLink>
        ))}
      </nav>
    </aside>
  );
}


export default Sidebar;