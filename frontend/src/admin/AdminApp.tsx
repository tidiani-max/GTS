import { FormEvent, useEffect, useRef, useState } from "react"
import { Link, NavLink, Navigate, Route, Routes, useLocation, useNavigate } from "react-router-dom"
import {
  BarChart3, Bell, BriefcaseBusiness, ChevronRight, FolderKanban, Gauge, LogOut, Menu, MessageSquare, Settings,
  ShieldCheck, Timer, Users, X,
} from "lucide-react"
import { api, errorMessage } from "../services/api"
import { useAuth } from "../services/auth"
import type { AppNotification } from "../types"
import { Loading, Toasts, fmtDateTime, initials, roleLabels, useResource } from "./ui"
import { Dashboard } from "./pages/Dashboard"
import { Inquiries } from "./pages/Inquiries"
import { Projects } from "./pages/Projects"
import { ServicesAdmin } from "./pages/ServicesAdmin"
import { Reports } from "./pages/Reports"
import { Team } from "./pages/Team"
import { AdminSettings } from "./pages/Settings"
import { Automation } from "./pages/Automation"
import { NotificationsPage } from "./pages/Notifications"

export function AdminLogin() {
  const navigate = useNavigate()
  const { login, user, loading, expired } = useAuth()
  const [error, setError] = useState("")
  const [busy, setBusy] = useState(false)
  if (!loading && user) return <Navigate to="/admin" replace />
  const submit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    const data = new FormData(e.currentTarget)
    const email = String(data.get("email") ?? "").trim()
    const password = String(data.get("password") ?? "")
    if (!email || !password) return setError("Renseignez votre email et votre mot de passe.")
    setBusy(true); setError("")
    try { await login(email, password); navigate("/admin") } catch (err) { setError(errorMessage(err)) } finally { setBusy(false) }
  }
  return (
    <main className="login-page">
      <section className="login-panel">
        <Link to="/"><img src="/assets/gst-logo.png" alt="Global Services Technologie" /></Link>
        <div className="login-icon"><ShieldCheck /></div>
        <h1>Administration GST</h1>
        <p>Accédez à l’espace de gestion interne</p>
        {expired && <p className="session-banner">Votre session a expiré. Veuillez vous reconnecter.</p>}
        <form onSubmit={submit}>
          <label>Adresse email<input name="email" type="email" autoComplete="username" /></label>
          <label>Mot de passe<input name="password" type="password" autoComplete="current-password" /></label>
          {error && <p className="form-error" role="alert">{error}</p>}
          <button className="admin-primary" disabled={busy}>{busy ? "Connexion…" : <>Se connecter <ChevronRight /></>}</button>
        </form>
        <small>Accès réservé au personnel autorisé. Les tentatives de connexion sont limitées et journalisées.</small>
        <Link className="back-site" to="/">← Retour au site public</Link>
      </section>
    </main>
  )
}

const navItems = [
  ["", "Tableau de bord", Gauge, "readonly"],
  ["demandes", "Demandes", MessageSquare, "readonly"],
  ["projets", "Projets", FolderKanban, "readonly"],
  ["services", "Services", BriefcaseBusiness, "readonly"],
  ["rapports", "Rapports", BarChart3, "readonly"],
  ["equipe", "Équipe", Users, "readonly"],
  ["automatisation", "Automatisation", Timer, "admin"],
  ["parametres", "Paramètres", Settings, "readonly"],
] as const

function Bell_() {
  const [open, setOpen] = useState(false)
  const nav = useNavigate()
  const ref = useRef<HTMLDivElement>(null)
  const n = useResource(() => api.notifications(), [], 30000)
  useEffect(() => {
    const close = (e: MouseEvent) => { if (!ref.current?.contains(e.target as Node)) setOpen(false) }
    document.addEventListener("mousedown", close)
    return () => document.removeEventListener("mousedown", close)
  }, [])
  const count = n.data?.unreadCount ?? 0
  const click = async (x: AppNotification) => {
    setOpen(false)
    if (!x.read) await api.markRead(x.id).catch(() => {})
    n.reload()
    if (x.link) nav(x.link)
  }
  return (
    <div className="bell-wrap" ref={ref}>
      <button aria-label="Notifications" onClick={() => { setOpen(!open); n.reload() }}>
        <Bell />{count > 0 && <i>{count > 99 ? "99+" : count}</i>}
      </button>
      {open && (
        <div className="bell-panel">
          <header>Notifications<button onClick={() => api.markAllRead().then(n.reload)}>Tout marquer comme lu</button></header>
          {n.data?.items.slice(0, 6).map((x) => (
            <button key={x.id} className={`notif-item ${x.read ? "" : "unread"}`} onClick={() => click(x)}>
              <b>{x.title}</b><span>{x.body.slice(0, 120)}</span><small>{fmtDateTime(x.createdAt)}</small>
            </button>
          ))}
          {!n.data?.items.length && <div className="empty"><p>Aucune notification.</p></div>}
          <footer><Link to="/admin/notifications" onClick={() => setOpen(false)}>Tout voir</Link></footer>
        </div>
      )}
    </div>
  )
}

export function AdminApp() {
  const { user, loading, logout, can } = useAuth()
  const [menu, setMenu] = useState(false)
  const loc = useLocation()
  const newCount = useResource(() => api.inquiries({ status: "Nouveau", pageSize: 1 }), [loc.pathname], 30000)
  if (loading) return <Loading />
  if (!user) return <Navigate to="/admin/login" replace />  // UX only: every API call is authorised server-side
  const signOut = async () => { await logout(); location.href = "/admin/login" }
  return (
    <div className="admin-shell">
      <Toasts />
      <aside className={menu ? "admin-sidebar open" : "admin-sidebar"}>
        <div className="admin-brand"><img src="/assets/gst-logo.png" alt="GST" /><button onClick={() => setMenu(false)}><X /></button></div>
        <p className="nav-label">GESTION</p>
        <nav>
          {navItems.filter(([, , , min]) => can(min)).map(([to, label, Icon]) => (
            <NavLink end={!to} key={label} to={`/admin/${to}`} onClick={() => setMenu(false)}>
              <Icon />{label}
              {label === "Demandes" && (newCount.data?.total ?? 0) > 0 && <b>{newCount.data!.total}</b>}
            </NavLink>
          ))}
        </nav>
        <div className="admin-user">
          <div>{initials(user.name)}</div>
          <span><b>{user.name}</b><small>{roleLabels[user.role]}</small></span>
          <button onClick={signOut} title="Déconnexion" aria-label="Déconnexion"><LogOut /></button>
        </div>
      </aside>
      <section className="admin-main">
        <header className="admin-header">
          <button className="admin-menu" onClick={() => setMenu(true)} aria-label="Menu"><Menu /></button>
          <div><p>ESPACE ADMINISTRATEUR</p><b>Global Services Technologie</b></div>
          <div className="header-tools"><Bell_ /><span>{initials(user.name)}</span></div>
        </header>
        <div className="admin-content">
          <Routes>
            <Route index element={<Dashboard />} />
            <Route path="demandes" element={<Inquiries />} />
            <Route path="projets" element={<Projects />} />
            <Route path="services" element={<ServicesAdmin />} />
            <Route path="rapports" element={<Reports />} />
            <Route path="equipe" element={<Team />} />
            <Route path="notifications" element={<NotificationsPage />} />
            <Route path="automatisation" element={can("admin") ? <Automation /> : <Navigate to="/admin" replace />} />
            <Route path="parametres" element={<AdminSettings />} />
            <Route path="*" element={<Navigate to="/admin" replace />} />
          </Routes>
        </div>
      </section>
    </div>
  )
}
