import { useState } from "react";
import { Link, NavLink } from "react-router-dom";
import { Shield, X, Menu, LayoutDashboard, Users, Sparkles, Plus } from "lucide-react";

export function Header() {
  const [menuOpen, setMenuOpen] = useState(false);
  return (
      <header className="topbar">
        <Link className="brand" to="/" aria-label="GoldSafe dashboard">
          <span className="brand-mark"><Shield size={22} strokeWidth={2.2} /></span>
          <span className="brand-copy">
            <strong>GoldSafe</strong>
            <small>MUTHOOT FINANCE AI</small>
          </span>
        </Link>
        <button
          type="button"
          className="mobile-menu"
          aria-label="Toggle navigation"
          aria-expanded={menuOpen}
          onClick={() => setMenuOpen(!menuOpen)}
        >
          {menuOpen ? <X size={20} /> : <Menu size={20} />}
        </button>
        <nav className={`main-nav ${menuOpen ? "open" : ""}`}>
          <NavLink end to="/" onClick={() => setMenuOpen(false)}><LayoutDashboard size={16} />Dashboard</NavLink>
          <NavLink to="/pledges" onClick={() => setMenuOpen(false)}><Users size={16} />Pledge Records</NavLink>
          <NavLink to="/identify" onClick={() => setMenuOpen(false)}><Sparkles size={16} />Identify</NavLink>
          <Link className="nav-cta" to="/register" onClick={() => setMenuOpen(false)}><Plus size={16} />Register Customer</Link>
        </nav>
      </header>
  );
}
