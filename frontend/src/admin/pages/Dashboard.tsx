import { Link } from "react-router-dom"
import { Area, AreaChart, CartesianGrid, Cell, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts"
import { Bell, FileText, FolderKanban, MessageSquare } from "lucide-react"
import { api } from "../../services/api"
import { Badge, ErrorBox, Loading, PageHead, fmtDate, initials, useResource } from "../ui"

export function Dashboard() {
  const ov = useResource(() => api.overview("6m"), [], 30000)
  const recent = useResource(() => api.inquiries({ pageSize: 4, sort: "-created_at" }), [], 30000)
  const projects = useResource(() => api.projects({ status: "En cours", pageSize: 3 }), [], 30000)
  if (ov.loading || recent.loading || projects.loading) return <Loading />
  if (ov.error || !ov.data) return <ErrorBox message={ov.error} onRetry={ov.reload} />
  const k = ov.data.kpis
  const cards = [
    ["Demandes totales", k.totalInquiries, MessageSquare,
      k.trendPct === null ? "30 derniers jours : " + k.last30Days : `${k.trendPct >= 0 ? "+" : ""}${k.trendPct}% sur 30 jours`, "blue"],
    ["À traiter", k.toTreat, FileText, k.overdue ? `${k.overdue} en retard de suivi` : "Action requise", "amber"],
    ["Messages non lus", k.unread, Bell, "À consulter", "purple"],
    ["Projets actifs", k.activeProjects, FolderKanban, "Suivi en cours", "green"],
  ] as const
  const pieColors = ["#0759c7", "#f0a11a", "#7654d4", "#21a366", "#df4b4b"]
  return (
    <>
      <PageHead eyebrow="VUE D’ENSEMBLE" title="Tableau de bord" description="Bienvenue. Voici l’activité opérationnelle de GST aujourd’hui." />
      <div className="metric-grid">
        {cards.map(([label, value, Icon, hint, color]) => (
          <article className={`metric ${color}`} key={label}>
            <div><p>{label}</p><strong>{value}</strong><span>{hint}</span></div>
            <Icon />
          </article>
        ))}
      </div>
      <div className="admin-grid wide">
        <section className="admin-card chart-card">
          <div className="card-head">
            <div><h2>Évolution des demandes</h2><p>Demandes reçues et résolues sur 6 mois</p></div>
            <Badge>6 derniers mois</Badge>
          </div>
          <ResponsiveContainer width="100%" height={280}>
            <AreaChart data={ov.data.trend}>
              <defs>
                <linearGradient id="blueFade" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#0759c7" stopOpacity=".35" />
                  <stop offset="100%" stopColor="#0759c7" stopOpacity=".02" />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" vertical={false} />
              <XAxis dataKey="month" /><YAxis allowDecimals={false} /><Tooltip />
              <Area type="monotone" dataKey="demandes" stroke="#0759c7" strokeWidth={3} fill="url(#blueFade)" />
              <Area type="monotone" dataKey="resolues" stroke="#21a366" strokeWidth={2} fill="transparent" />
            </AreaChart>
          </ResponsiveContainer>
        </section>
        <section className="admin-card status-summary">
          <div className="card-head"><div><h2>Répartition</h2><p>Statut des demandes</p></div></div>
          <ResponsiveContainer width="100%" height={180}>
            <PieChart>
              <Pie data={ov.data.byStatus} innerRadius={52} outerRadius={76} dataKey="value" nameKey="name">
                {pieColors.map((c) => <Cell key={c} fill={c} />)}
              </Pie>
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
          <div className="resolution"><strong>{k.resolutionRate}%</strong><span>taux de résolution</span></div>
        </section>
      </div>
      <div className="admin-grid">
        <section className="admin-card">
          <div className="card-head">
            <div><h2>Demandes récentes</h2><p>Dernières soumissions clients</p></div>
            <Link to="/admin/demandes">Tout voir</Link>
          </div>
          <div className="activity-list">
            {recent.data?.items.length ? recent.data.items.map((i) => (
              <div key={i.id}>
                <span className="avatar">{initials(i.name)}</span>
                <p><b>{i.name}</b><small>{i.service} · {i.id}</small></p>
                <Badge>{i.status}</Badge>
              </div>
            )) : <div className="empty"><p>Aucune demande pour le moment.</p></div>}
          </div>
        </section>
        <section className="admin-card">
          <div className="card-head">
            <div><h2>Projets en cours</h2><p>Progression opérationnelle</p></div>
            <Link to="/admin/projets">Gérer</Link>
          </div>
          <div className="project-mini">
            {projects.data?.items.length ? projects.data.items.map((p) => (
              <div key={p.id}>
                <p><b>{p.name}</b><span>{p.progress}%</span></p>
                <div><i style={{ width: `${p.progress}%` }} /></div>
                <small>{p.client || ""} · Échéance {fmtDate(p.deadline)}</small>
              </div>
            )) : <div className="empty"><p>Aucun projet en cours.</p></div>}
          </div>
        </section>
      </div>
    </>
  )
}
