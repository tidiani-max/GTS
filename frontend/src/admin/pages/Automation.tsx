import { useEffect, useState } from "react"
import { Play, Eye } from "lucide-react"
import { api } from "../../services/api"
import { useAuth } from "../../services/auth"
import type { AutomationConfig, JobRun } from "../../types"
import { Badge, ErrorBox, Loading, PageHead, fmtDateTime, toast, useResource } from "../ui"

const DAYS = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]

export function Automation() {
  const { can } = useAuth()
  const status = useResource(() => api.automationStatus(), [], 15000)
  const [tab, setTab] = useState<"jobs" | "runs" | "emails" | "config">("jobs")
  const [page, setPage] = useState(1)
  const runs = useResource(() => api.jobRuns(page), [page, tab], tab === "runs" ? 10000 : 0)
  const emails = useResource(() => api.emails(page), [page, tab], 0)
  const [cfg, setCfg] = useState<AutomationConfig | null>(null)
  const [recipients, setRecipients] = useState("")
  const [busy, setBusy] = useState("")
  const [last, setLast] = useState<JobRun | null>(null)
  useEffect(() => { if (status.data && !cfg) { setCfg(status.data.config); setRecipients(status.data.config.extraRecipients.join(", ")) } }, [status.data, cfg])
  if (status.loading && !status.data) return <Loading />
  if (status.error && !status.data) return <ErrorBox message={status.error} onRetry={status.reload} />
  const s = status.data!
  const run = async (name: string, dry: boolean) => {
    if (!dry && !confirm("Exécuter réellement cette tâche maintenant (notifications/emails créés) ?")) return
    setBusy(name + dry)
    try { const r = await api.runJob(name, dry); setLast(r); toast.ok(dry ? "Simulation terminée (aucune modification)" : "Tâche exécutée"); status.reload(); runs.reload() }
    catch (e) { toast.err(e) } finally { setBusy("") }
  }
  const saveCfg = async () => {
    if (!cfg) return
    try {
      const extra = recipients.split(/[,;\s]+/).filter(Boolean)
      const saved = await api.saveAutomation({ ...cfg, extraRecipients: extra }); setCfg(saved); toast.ok("Configuration enregistrée"); status.reload()
    } catch (e) { toast.err(e) }
  }
  const num = (k: keyof AutomationConfig, label: string, min: number, max: number) => (
    <label>{label}<input type="number" min={min} max={max} value={Number(cfg![k])} onChange={(e) => setCfg({ ...cfg!, [k]: Number(e.target.value) })} /></label>
  )
  const chk = (k: keyof AutomationConfig, label: string) => (
    <label className="check"><input type="checkbox" checked={!!cfg![k]} onChange={(e) => setCfg({ ...cfg!, [k]: e.target.checked })} />{label}</label>
  )
  const edit = can("admin")
  return (
    <>
      <PageHead eyebrow="AUTOMATISATION" title="Tâches automatiques" description={`Rappels, alertes et résumés. Mode email : ${s.emailMode}${s.emailMode === "console" ? " (les emails sont seulement journalisés)" : ""}.`} />
      <div className="tabs">
        {([["jobs", "Tâches"], ["runs", "Journal d’exécution"], ["emails", "Emails"], ["config", "Configuration"]] as const).map(([k, l]) => (
          <button key={k} className={tab === k ? "on" : ""} onClick={() => { setTab(k); setPage(1) }}>{l}</button>
        ))}
      </div>
      {tab === "jobs" && (
        <>
          <div className="auto-grid">
            {s.jobs.map((j) => (
              <article className="admin-card job-card" key={j.name}>
                <h3>{j.label}</h3>
                <small>Dernière exécution : {j.lastRun ? fmtDateTime(j.lastRun.startedAt) : "jamais"} {j.lastRun && <Badge>{j.lastRun.status}</Badge>}</small>
                <small>Prochaine échéance : {fmtDateTime(j.nextDue)} · échecs : {j.failedRuns}</small>
                {j.lastRun?.error && <small className="list-error">{j.lastRun.error}</small>}
                {edit && (
                  <div className="row">
                    <button className="admin-secondary" disabled={!!busy} onClick={() => run(j.name, true)}><Eye />Simuler</button>
                    <button className="admin-primary" disabled={!!busy} onClick={() => run(j.name, false)}><Play />Exécuter</button>
                  </div>
                )}
              </article>
            ))}
          </div>
          {last && <section className="admin-card settings-card"><h2>Résultat · {last.job} {last.dryRun ? "(simulation)" : ""}</h2><pre className="pre-json">{JSON.stringify(last.summary, null, 2)}</pre></section>}
          <p style={{ fontSize: 10, color: "#667085" }}>Emails : {Object.entries(s.outbox).map(([k, v]) => `${k} ${v}`).join(" · ") || "aucun"}</p>
        </>
      )}
      {tab === "runs" && (
        <section className="admin-card table-card">
          <div className="table-wrap"><table>
            <thead><tr><th>Date</th><th>Tâche</th><th>Déclencheur</th><th>Statut</th><th>Résumé / erreur</th></tr></thead>
            <tbody>{runs.data?.items.map((r) => (
              <tr key={r.id}><td>{fmtDateTime(r.startedAt)}</td><td>{r.job}</td><td>{r.trigger}{r.dryRun ? " · simulation" : ""}</td>
                <td><Badge>{r.status}</Badge></td>
                <td>{r.error ? <span className="list-error">{r.error}</span> : <pre className="pre-json">{JSON.stringify(r.summary)}</pre>}</td></tr>
            ))}</tbody>
          </table></div>
          {!runs.data?.items.length && <div className="empty"><p>Aucune exécution enregistrée. Le worker exécute les tâches selon leur planification.</p></div>}
          <Pager page={page} pages={runs.data?.pages ?? 1} setPage={setPage} />
        </section>
      )}
      {tab === "emails" && (
        <section className="admin-card table-card">
          <div className="table-wrap"><table>
            <thead><tr><th>Date</th><th>Destinataire</th><th>Sujet</th><th>Statut</th><th>Tentatives</th><th>Erreur</th></tr></thead>
            <tbody>{emails.data?.items.map((m) => (
              <tr key={m.id}><td>{fmtDateTime(m.createdAt)}</td><td>{m.toEmail}</td><td>{m.subject}</td><td><Badge>{m.status}</Badge></td><td>{m.attempts}</td><td>{m.lastError}</td></tr>
            ))}</tbody>
          </table></div>
          {!emails.data?.items.length && <div className="empty"><p>Aucun email en file.</p></div>}
          <Pager page={page} pages={emails.data?.pages ?? 1} setPage={setPage} />
        </section>
      )}
      {tab === "config" && cfg && (
        <section className="admin-card">
          <fieldset disabled={!edit} style={{ border: 0, margin: 0, padding: 0 }}>
            <div className="cfg-grid">
              {chk("remindersEnabled", "Rappels de relance activés")}
              {num("remindersEveryMinutes", "Vérification des rappels (minutes)", 5, 1440)}
              {num("reminderLeadDays", "Rappeler N jours avant l’échéance", 0, 14)}
              {num("reminderMinGapHours", "Délai minimal entre deux rappels (h)", 1, 168)}
              {num("maxReminders", "Nombre maximal de rappels par demande", 1, 20)}
              {chk("overdueEnabled", "Alerte quotidienne des retards")}
              {num("overdueEveryMinutes", "Vérification des retards (minutes)", 15, 1440)}
              {chk("newInquiryEnabled", "Notifier chaque nouvelle demande")}
              {chk("notifyAssignee", "Rappels envoyés au responsable assigné")}
              {chk("summaryEnabled", "Résumé hebdomadaire")}
              <label>Jour du résumé<select value={cfg.summaryWeekday} onChange={(e) => setCfg({ ...cfg, summaryWeekday: Number(e.target.value) })}>{DAYS.map((d, i) => <option key={d} value={i}>{d}</option>)}</select></label>
              {num("summaryHour", "Heure du résumé (UTC)", 0, 23)}
              {chk("cleanupEnabled", "Nettoyage des données techniques")}
              {num("retentionDays", "Conservation (jours)", 7, 3650)}
              {chk("dryRun", "Mode simulation global (le worker ne fait que simuler)")}
              <label style={{ gridColumn: "1/-1" }}>Destinataires email supplémentaires (séparés par des virgules)
                <input value={recipients} onChange={(e) => setRecipients(e.target.value)} placeholder="direction@exemple.ml" /></label>
            </div>
          </fieldset>
          {edit && <div className="modal-actions"><button className="admin-primary" onClick={saveCfg}>Enregistrer la configuration</button></div>}
        </section>
      )}
    </>
  )
}

function Pager({ page, pages, setPage }: { page: number; pages: number; setPage: (n: number) => void }) {
  return (
    <div className="pagination"><span>Page {page} / {pages}</span>
      <div><button disabled={page === 1} onClick={() => setPage(page - 1)}>Précédent</button><b>{page}</b>
        <button disabled={page >= pages} onClick={() => setPage(page + 1)}>Suivant</button></div></div>
  )
}
