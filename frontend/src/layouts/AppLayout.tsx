import { NavLink, Outlet } from "react-router-dom";

import { useAuth } from "../auth/AuthContext";

export function AppLayout() {
  const { user, logout } = useAuth();

  return (
    <div className="app-shell">
      <header className="app-header">
        <div className="app-header-title">FAQ Chatbot</div>
        <nav className="app-nav">
          <NavLink to="/" end>Ask</NavLink>
          <NavLink to="/faqs">FAQ Entries</NavLink>
        </nav>
        <div className="app-header-user">
          <span>{user?.email}</span>
          <button onClick={logout}>Log out</button>
        </div>
      </header>
      <main className="app-content">
        <Outlet />
      </main>
    </div>
  );
}
