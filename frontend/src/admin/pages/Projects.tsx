import { useState } from "react"
import { Download, Plus, Trash2, X } from "lucide-react"
import { api } from "../../services/api"
import { useAuth } from "../../services/auth"
import type { Project, ProjectStatus } from "../../types"
import { Badge, ErrorBox, Loading, PageHead, fmtDate, toast, useResource } from "../ui"

const blank = { id: "", name: "Nouveau projet", client: "", service: "", status: "Planifié" as ProjectStatus, progress: 0,
  deadline: new Date().toISOString().slice(0, 10), lead: "Non assigné", leadId: null as number | null, isDemo: false }

export function Projects() {
  const { can } = useAuth()
  const [q, setQ] = useState("")
  const [status, setStatus] = useState("")
  const [editing, setEditing] = useState<Project | null>(null)
  const list = useResource(() => api.projects({ q, status }), [q, status], 30000)
  const team = useResource(() => api.users(), [])
  if (list.loading && !list.data) return <Loading />
  if (list.error && !list.data) return <ErrorBox message={list.error} onRetry={list.reload} />
  const projects = list.data?.items ?? []
  const save = async (p: Project) => {
    try {
      await api.saveProject(p.id || null, {
        name: p.name, client: p.client, service: p.service, status: p.status, progress: p.progress,
        deadline: p.deadline || null, leadId: p.leadId,
      })
      toast.ok("Projet enregistré"); setEditing(null); list.reload()
    } catch (e) { toast.err(e) }
  }
  const remove = async (p: Project) => {
    if (!confirm(`Supprimer le projet « ${p.name} » ?`)) return
    try { await api.deleteProject(p.id); toast.ok("Projet supprimé"); setEditing(null); list.reload() } catch (e) { toast.err(e) }
  }
  return (
    <>
      <PageHead eyebrow="OPÉRATIONS" title="Projets" description="Pilotez les projets, échéances et équipes assignées."
        action={<div className="head-actions">
          <button className="admin-secondary" onClick={() => api.exportProjects().catch(toast.err)}><Download />CSV</button>
          {can("admin") && <button className="admin-primary" onClick={() => setEditing({ ...blank })}><Plus />Nouveau projet</button>}
        </div>} />
      <div className="filter-bar">
        <label className="search"><input placeholder="Rechercher un projet, un client…" value={q} onChange={(e) => setQ(e.target.value)} /></label>
        <select aria-label="Statut" value={status} onChange={(e) => setStatus(e.target.value)}>
          <option value="">Tous les statuts</option>
          {["Planifié", "En cours", "Suspendu", "Terminé"].map((s) => <option key={s}>{s}</option>)}
        </select>
      </div>
      {!projects.length && <div className="empty"><h3>Aucun projet</h3><p>Créez un projet pour commencer le suivi.</p></div>}
      <div className="project-grid">
        {projects.map((p) => (
          <article className="admin-card project-card" key={p.id} onClick={() => setEditing(p)}>
            <div><Badge>{p.status}</Badge><span>{p.id}{p.isDemo && <em className="demo-tag">DÉMO</em>}</span></div>
            <h2>{p.name}</h2>
            <p>{p.client || ""}</p>
            <dl>
              <div><dt>Service</dt><dd>{p.service || ""}</dd></div>
              <div><dt>Responsable</dt><dd>{p.lead}</dd></div>
              <div><dt>Échéance</dt><dd>{fmtDate(p.deadline)}</dd></div>
            </dl>
            <div className="progress-label"><span>Progression</span><b>{p.progress}%</b></div>
            <div className="progress"><i style={{ width: `${p.progress}%` }} /></div>
          </article>
        ))}
      </div>
      {editing && (
        <ProjectModal project={editing} team={team.data ?? []} canEdit={can(editing.id ? "staff" : "admin")}
          canDelete={can("admin") && !!editing.id} onClose={() => setEditing(null)} onSave={save} onDelete={() => remove(editing)} />
      )}
    </>
  )
}

function ProjectModal({ project, team, canEdit, canDelete, onClose, onSave, onDelete }: {
  project: Project; team: { id: number; name: string; active: boolean }[]; canEdit: boolean; canDelete: boolean
  onClose: () => void; onSave: (p: Project) => void; onDelete: () => void
}) {
  const [p, setP] = useState(project)
  const full = canEdit
  return (
    <div className="modal-backdrop">
      <form className="admin-modal" onSubmit={(e) => { e.preventDefault(); onSave(p) }}>
        <div className="drawer-head">
          <div><p>{p.id || "Nouveau"}</p><h2>Projet</h2></div>
          <button type="button" onClick={onClose} aria-label="Fermer"><X /></button>
        </div>
        <fieldset disabled={!full} style={{ border: 0, padding: 0, margin: 0 }}>
          <div className="modal-fields">
            <label>Nom du projet<input required minLength={2} value={p.name} onChange={(e) => setP({ ...p, name: e.target.value })} /></label>
            <label>Client<input value={p.client} onChange={(e) => setP({ ...p, client: e.target.value })} /></label>
            <label>Service<input value={p.service} onChange={(e) => setP({ ...p, service: e.target.value })} /></label>
            <label>Statut
              <select value={p.status} onChange={(e) => setP({ ...p, status: e.target.value as ProjectStatus })}>
                {["Planifié", "En cours", "Suspendu", "Terminé"].map((x) => <option key={x}>{x}</option>)}
              </select>
            </label>
            <label>Responsable
              <select value={p.leadId ?? ""} onChange={(e) => setP({ ...p, leadId: e.target.value ? Number(e.target.value) : null })}>
                <option value="">Non assigné</option>
                {team.filter((t) => t.active || t.id === p.leadId).map((t) => <option key={t.id} value={t.id}>{t.name}</option>)}
              </select>
            </label>
            <label>Échéance<input type="date" value={p.deadline ?? ""} onChange={(e) => setP({ ...p, deadline: e.target.value || null })} /></label>
            <label className="full">Progression  {p.progress}%
              <input type="range" min="0" max="100" value={p.progress} onChange={(e) => setP({ ...p, progress: Number(e.target.value) })} />
            </label>
          </div>
        </fieldset>
        <div className="modal-actions">
          {canDelete && <button type="button" className="danger-link" style={{ marginRight: "auto" }} onClick={onDelete}><Trash2 size={14} /> Supprimer</button>}
          <button type="button" className="admin-secondary" onClick={onClose}>Annuler</button>
          {canEdit && <button className="admin-primary">Enregistrer</button>}
        </div>
      </form>
    </div>
  )
}
