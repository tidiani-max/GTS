import { useState } from "react"
import { Area, AreaChart, CartesianGrid, Cell, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts"
import { Activity, Check, Download, FolderKanban } from "lucide-react"
import { api } from "../../services/api"
import { ErrorBox, Loading, PageHead, toast, useResource } from "../ui"

const RANGES: [string, string][] = [["30d", "30 derniers jours"], ["3m", "3 derniers mois"], ["6m", "6 derniers mois"], ["12m", "12 derniers mois"]]

export function Reports() {
  const [range, setRange] = useState("6m")
  const ov = useResource(() => api.overview(range), [range], 60000)
  if (ov.loading && !ov.data) return <Loading />
  if (ov.error && !ov.data) return <ErrorBox message={ov.error} onRetry={ov.reload} />
  const d = ov.data!
  const label = RANGES.find(([v]) => v === range)![1]
  const colors = ["#0759c7", "#21a366", "#7654d4", "#f0a11a", "#16a0b8"]
  return (
    <>
      <PageHead eyebrow="ANALYSE" title="Rapports & statistiques" description="Analysez l’activité et exportez les données consolidées."
        action={<div className="head-actions">
          <select aria-label="Période" value={range} onChange={(e) => setRange(e.target.value)}>
            {RANGES.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
          </select>
          <button className="admin-secondary" onClick={() => api.exportReport(range).catch(toast.err)}><Download />CSV</button>
        </div>} />
      <div className="metric-grid report-metrics">
        <article className="metric blue"><div><p>Taux de résolution</p><strong>{d.kpis.resolutionRate}%</strong><span>{d.kpis.totalInquiries} demandes au total</span></div><Check /></article>
        <article className="metric green"><div><p>Projets terminés</p><strong>{d.kpis.completedProjects}</strong><span>sur {d.kpis.totalProjects} projets</span></div><FolderKanban /></article>
        <article className="metric purple"><div><p>Délai moyen</p>
          <strong>{d.kpis.avgResolutionDays === null ? "" : `${String(d.kpis.avgResolutionDays).replace(".", ",")} j`}</strong>
          <span>{label} · demandes résolues</span></div><Activity /></article>
      </div>
      <div className="admin-grid">
        <section className="admin-card chart-card">
          <div className="card-head"><div><h2>Activité mensuelle</h2><p>Demandes et résolutions</p></div></div>
          <ResponsiveContainer width="100%" height={290}>
            <AreaChart data={d.trend}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} /><XAxis dataKey="month" /><YAxis allowDecimals={false} /><Tooltip />
              <Area dataKey="demandes" stroke="#0759c7" fill="#d8e7f8" /><Area dataKey="resolues" stroke="#21a366" fill="#d9f2e5" />
            </AreaChart>
          </ResponsiveContainer>
        </section>
        <section className="admin-card chart-card">
          <div className="card-head"><div><h2>Demandes par service</h2><p>{label}</p></div></div>
          {d.byService.length ? (
            <ResponsiveContainer width="100%" height={290}>
              <PieChart>
                <Pie data={d.byService} dataKey="value" nameKey="name" outerRadius={95} label>
                  {d.byService.map((_, i) => <Cell key={i} fill={colors[i % colors.length]} />)}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          ) : <div className="empty"><p>Aucune demande sur cette période.</p></div>}
        </section>
      </div>
    </>
  )
}
