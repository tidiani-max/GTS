import { useState } from "react"
import { Link, NavLink, Outlet, useLocation } from "react-router-dom"
import { Mail, Menu, X } from "lucide-react"

const links = [
  ["/", "Accueil"],
  ["/a-propos", "À propos"],
  ["/references", "Nos références"],
  ["/services", "Nos services"],
  ["/contact", "Contact"],
]

export function PublicLayout() {
  const [open, setOpen] = useState(false)
  const contact = useLocation().pathname === "/contact"
  return (
    <div className={contact ? "contact-theme" : ""}>
      <header className="site-header">
        <div className="header-inner">
          <Link
            to="/"
            className="brand"
            aria-label="Global Services Technologie  Accueil"
          >
            <img src="/assets/gst-logo.png" alt="Global Services Technologie" />
          </Link>
          <button
            className="menu-button"
            onClick={() => setOpen(!open)}
            aria-label="Ouvrir le menu"
            aria-expanded={open}
          >
            {open ? <X /> : <Menu />}
          </button>
          <nav
            className={open ? "site-nav open" : "site-nav"}
            aria-label="Navigation principale"
          >
            {links.map(([to, label], i) => (
              <NavLink key={to} to={to} onClick={() => setOpen(false)}>
                {label}
                {i < links.length - 1 && <span>•</span>}
              </NavLink>
            ))}
            <Link className="admin-link" to="/admin">
              Espace admin
            </Link>
          </nav>
        </div>
      </header>
      <main>
        <Outlet />
      </main>
      <footer className="site-footer">
        <div>
          <h3>ADRESSE</h3>
          <p>Hamdallaye ACI-2000 · Rue 420 Porte 437 · BP 2485 Bamako, Mali</p>
          <p>
            Email: dcheick93@hotmail.com <Mail size={13} />
          </p>
          <small>
            © 2024 GLOBAL SERVICES TECHNOLOGIE  Tous droits réservés
          </small>
        </div>
        <div className="partners">
          <h3>PARTENAIRES</h3>
          <div>
            <span className="orange">Orange</span>
            <span className="ieng">ieng.</span>
            <span className="public">
              Services
              <br />
              Publics
            </span>
            <span className="ong">ONG</span>
          </div>
        </div>
      </footer>
    </div>
  )
}

export function Hero({
  eyebrow,
  title,
  subtitle,
  description,
  primary = "Découvrir nos services",
  secondary = "Nous contacter",
  dark = false,
  primaryTo = "/services",
  secondaryTo = "/contact",
}: {
  eyebrow?: string
  title: string
  subtitle: string
  description?: string
  primary?: string
  secondary?: string
  dark?: boolean
  primaryTo?: string
  secondaryTo?: string
}) {
  return (
    <section className={`hero ${dark ? "dark" : ""}`}>
      <div className="hero-copy">
        {eyebrow && <p className="eyebrow">{eyebrow}</p>}
        <h1>{title}</h1>
        <h2>{subtitle}</h2>
        {description && <p className="hero-description">{description}</p>}
        <div className="hero-actions">
          <Link className="button primary" to={primaryTo}>
            {primary}
          </Link>
          <a className="button secondary" href={secondaryTo}>
            {secondary}
          </a>
        </div>
      </div>
      <img
        className="hero-image"
        src="/assets/gst-control-room.jpg"
        alt="Centre de supervision technologique GST"
      />
    </section>
  )
}

export function SectionTitle({
  title,
  subtitle,
}: {
  title: string
  subtitle: string
}) {
  return (
    <div className="section-title">
      <h2>{title}</h2>
      <p>{subtitle}</p>
    </div>
  )
}
