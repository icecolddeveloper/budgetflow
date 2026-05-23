import {
  ArrowRightLeft,
  LayoutGrid,
  LogOut,
  Menu,
  PieChart,
  Plus,
  Sparkles,
  X,
} from "lucide-react";
import { useEffect, useState } from "react";
import { NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";

import { useAuth } from "../context/AuthContext";
import { ThemeToggle } from "./ThemeToggle";

const navigation = [
  { to: "/dashboard", label: "Dashboard", icon: LayoutGrid },
  { to: "/categories", label: "Categories", icon: PieChart },
  { to: "/transactions", label: "Transactions", icon: ArrowRightLeft },
];

const pageMeta = {
  "/dashboard": {
    title: "Financial hub",
    description: "Here's how your money's doing right now.",
  },
  "/categories": {
    title: "Your categories",
    description: "Adjust your envelopes, set targets, and pick colors that fit.",
  },
  "/transactions": {
    title: "Your transactions",
    description: "Every dollar in, out, and across your envelopes — all in one place.",
  },
};

export function AppShell() {
  const { user, logout } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const [menuOpen, setMenuOpen] = useState(false);

  const currentMeta = pageMeta[location.pathname] || pageMeta["/dashboard"];
  const initial =
    user?.first_name?.trim()?.[0]?.toUpperCase() ||
    user?.username?.slice(0, 1)?.toUpperCase() ||
    "U";

  useEffect(() => {
    setMenuOpen(false);
  }, [location.pathname]);

  useEffect(() => {
    if (!menuOpen) return undefined;
    const handler = (event) => {
      if (event.key === "Escape") setMenuOpen(false);
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [menuOpen]);

  function handleLogout() {
    logout();
    navigate("/auth", { replace: true });
  }

  return (
    <div className="app-shell">
      <aside className="app-sidebar">
        <div className="brand-mark">
          <span className="brand-mark__badge">
            <Sparkles size={18} />
          </span>
          <div>
            <strong>BudgetFlow</strong>
            <p>Your friendly money companion</p>
          </div>
        </div>

        <nav className="nav-stack" aria-label="Primary navigation">
          {navigation.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink
                key={item.to}
                to={item.to}
                className={({ isActive }) => `nav-link ${isActive ? "nav-link--active" : ""}`}
              >
                <Icon size={18} />
                <span>{item.label}</span>
              </NavLink>
            );
          })}
        </nav>

        <div className="sidebar-cta">
          <p>Got something new to log? Income, expense, or a quick transfer — add it from here.</p>
          <button type="button" className="btn btn-secondary" onClick={() => navigate("/transactions")}>
            <Plus size={16} />
            Add a transaction
          </button>
        </div>
      </aside>

      <div className="app-main">
        <header className="app-header">
          <div className="app-header__brand-mobile">
            <span className="brand-mark__badge">
              <Sparkles size={16} />
            </span>
            <strong>BudgetFlow</strong>
          </div>

          <div className="app-header__titles">
            <span className="eyebrow">Your money</span>
            <h1>{currentMeta.title}</h1>
            <p>{currentMeta.description}</p>
          </div>

          <div className="app-header__actions">
            <ThemeToggle />
            <div className="user-pill">
              <span>{initial}</span>
              <div>
                <strong>{user?.first_name || user?.username}</strong>
                <p>{user?.email || "Signed in"}</p>
              </div>
            </div>
            <button type="button" className="btn btn-ghost" onClick={handleLogout}>
              <LogOut size={16} />
              Sign out
            </button>
          </div>

          <button
            type="button"
            className="mobile-menu-button"
            onClick={() => setMenuOpen(true)}
            aria-label="Open menu"
            aria-expanded={menuOpen}
          >
            <Menu size={20} />
          </button>
        </header>

        <Outlet />
      </div>

      {menuOpen ? (
        <>
          <div
            className="mobile-drawer-backdrop"
            onClick={() => setMenuOpen(false)}
            aria-hidden="true"
          />
          <aside
            className="mobile-drawer"
            role="dialog"
            aria-modal="true"
            aria-label="Menu"
          >
            <div className="mobile-drawer__header">
              <div className="brand-mark">
                <span className="brand-mark__badge">
                  <Sparkles size={16} />
                </span>
                <strong>BudgetFlow</strong>
              </div>
              <button
                type="button"
                className="icon-button"
                onClick={() => setMenuOpen(false)}
                aria-label="Close menu"
              >
                <X size={18} />
              </button>
            </div>

            <div className="mobile-drawer__user">
              <span className="mobile-drawer__avatar">{initial}</span>
              <div>
                <strong>{user?.first_name || user?.username}</strong>
                <p>{user?.email || "Signed in"}</p>
              </div>
            </div>

            <nav className="mobile-drawer__nav" aria-label="Primary navigation">
              {navigation.map((item) => {
                const Icon = item.icon;
                return (
                  <NavLink
                    key={item.to}
                    to={item.to}
                    className={({ isActive }) =>
                      `mobile-drawer__link ${isActive ? "mobile-drawer__link--active" : ""}`
                    }
                  >
                    <Icon size={18} />
                    <span>{item.label}</span>
                  </NavLink>
                );
              })}
            </nav>

            <div className="mobile-drawer__footer">
              <div className="mobile-drawer__row">
                <span>Theme</span>
                <ThemeToggle />
              </div>
              <button type="button" className="btn btn-ghost btn-block" onClick={handleLogout}>
                <LogOut size={16} />
                Sign out
              </button>
            </div>
          </aside>
        </>
      ) : null}
    </div>
  );
}
