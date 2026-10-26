import { useState } from "react"
import { BriefcaseBusiness, Plus, Trash2 } from "lucide-react"
import { api } from "../../services/api"
import { useAuth } from "../../services/auth"
import type { Service } from "../../types"
import { ErrorBox, Loading, PageHead, toast, useResource } from "../ui"

export function ServicesAdmin() {
  const { can } = useAuth()
  const list = useResource(() => api.services(), [])
  const [drafts, setDrafts] = useState<Record<string, Partial<Service>>>({})
  const editable = can("admin")
  if (list.loading && !list.data) return <Loading />
  if (list.error && !list.data) return <ErrorBox message={list.error} onRetry={list.reload} />
  const items = list.data ?? []
  const draft = (s: Service) => ({ ...s, ...drafts[s.id] })
  const setField = (id: string, patch: Partial<Service>) => setDrafts((d) => ({ ...d, [id]: { ...d[id], ...patch } }))
  const persist = async (s: Service, patch: Partial<Service>) => {
    try {
      const saved = await api.saveService(s.id, patch)
      list.setData(items.map((x) => (x.id === s.id ? saved : x)))
      setDrafts((d) => { const { [s.id]: _, ...rest } = d; return rest })
      toast.ok("Service enregistré")
    } catch (e) { toast.err(e) }
  }
  const add = async () => {
    try { await api.saveService(null, { title: "Nouvelle offre", description: "Description à compléter.", active: false }); list.reload() }
    catch (e) { toast.err(e) }
  }
  const remove = async (s: Service) => {
    if (!confirm(`Supprimer le service « ${s.title} » ?`)) return
    try { await api.deleteService(s.id); toast.ok("Service supprimé"); list.reload() } catch (e) { toast.err(e) }
  }
  return (
    <>
      <PageHead eyebrow="CATALOGUE" title="Services" description="Gérez les offres proposées sur le site public (seules les offres actives sont proposées dans le formulaire de contact)."
        action={editable ? <button className="admin-primary" onClick={add}><Plus />Ajouter</button> : undefined} />
      {!items.length && <div className="empty"><h3>Aucun service</h3><p>Ajoutez votre première offre.</p></div>}
      <div className="service-admin-list">
        {items.map((s) => {
          const d = draft(s)
          const dirty = !!drafts[s.id]
          return (
            <article className="admin-card" key={s.id}>
              <div className="service-icon"><BriefcaseBusiness /></div>
              <div>
                <small>{s.id}</small>
                <input disabled={!editable} value={d.title} onChange={(e) => setField(s.id, { title: e.target.value })} />
                <textarea disabled={!editable} value={d.description} onChange={(e) => setField(s.id, { description: e.target.value })} />
                {editable && dirty && (
                  <button className="admin-primary" style={{ marginTop: 8 }} onClick={() => persist(s, { title: d.title, description: d.description })}>Enregistrer</button>
                )}
                {editable && <button className="danger-link" style={{ marginTop: 8, marginLeft: 8 }} onClick={() => remove(s)}><Trash2 size={13} /> Supprimer</button>}
              </div>
              <label className="switch" title={s.active ? "Actif" : "Inactif"}>
                <input type="checkbox" disabled={!editable} checked={s.active} onChange={(e) => persist(s, { active: e.target.checked })} />
                <i />
              </label>
            </article>
          )
        })}
      </div>
    </>
  )
}
