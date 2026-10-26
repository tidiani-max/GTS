import { useEffect, useState } from "react"
import { useSearchParams } from "react-router-dom"
import { Activity, Check, ChevronRight, Download, Plus, Search, SlidersHorizontal, Trash2, X } from "lucide-react"
import { api } from "../../services/api"
import { useAuth } from "../../services/auth"
import type { HistoryEvent, Inquiry, InquiryStatus, Priority, TeamMember } from "../../types"
import { Badge, ErrorBox, Loading, PageHead, TRANSITIONS, fmtDate, fmtDateTime, initials, priorities, statuses, toast, useResource } from "../ui"

const PAGE_SIZE = 8
const actionLabel: Record<string, string> = {
  created: "Demande créée", updated: "Mise à jour", status_changed: "Changement de statut", note_added: "Note ajoutée", deleted: "Supprimée",
}

export function Inquiries() {
  const { can } = useAuth()
  const [params, setParams] = useSearchParams()
  const [query, setQuery] = useState("")
  const [debounced, setDebounced] = useState("")
  const [status, setStatus] = useState("Tous")
  const [priority, setPriority] = useState("Toutes")
  const [assignee, setAssignee] = useState("")
  const [overdue, setOverdue] = useState(params.get("overdue") === "1")
  const [sort, setSort] = useState("-created_at")
  const [page, setPage] = useState(1)
  const [selected, setSelected] = useState<string | null>(params.get("ref"))
  const team = useResource(() => api.users(), [])

  useEffect(() => { const t = setTimeout(() => { setDebounced(query); setPage(1) }, 300); return () => clearTimeout(t) }, [query])
  const q = {
    q: debounced, status: status === "Tous" ? "" : status, priority: priority === "Toutes" ? "" : priority,
    assigneeId: assignee, overdue: overdue || undefined, sort, page, pageSize: PAGE_SIZE,
  }
  const list = useResource(() => api.inquiries(q), [debounced, status, priority, assignee, overdue, sort, page], 30000)
  const closeDrawer = () => { setSelected(null); if (params.get("ref")) setParams({}) }
  const exportCsv = () => api.exportInquiries(q).catch(toast.err)
  const data = list.data

  return (
    <>
      <PageHead eyebrow="RELATION CLIENT" title="Demandes & messages" description="Consultez, filtrez et traitez les demandes reçues."
        action={<button className="admin-secondary" onClick={exportCsv}><Download />Exporter CSV</button>} />
      <div className="filter-bar">
        <label className="search">
          <Search />
          <input placeholder="Rechercher un nom, une société, un service…" value={query} onChange={(e) => setQuery(e.target.value)} />
        </label>
        <SlidersHorizontal />
        <select aria-label="Statut" value={status} onChange={(e) => { setStatus(e.target.value); setPage(1) }}>
          <option>Tous</option>{statuses.map((s) => <option key={s}>{s}</option>)}
        </select>
        <select aria-label="Priorité" value={priority} onChange={(e) => { setPriority(e.target.value); setPage(1) }}>
          <option>Toutes</option>{priorities.map((s) => <option key={s}>{s}</option>)}
        </select>
        <select aria-label="Responsable" value={assignee} onChange={(e) => { setAssignee(e.target.value); setPage(1) }}>
          <option value="">Tous les responsables</option><option value="none">Non assigné</option>
          {team.data?.map((t) => <option key={t.id} value={t.id}>{t.name}</option>)}
        </select>
        <select aria-label="Tri" value={sort} onChange={(e) => setSort(e.target.value)}>
          <option value="-created_at">Plus récentes</option><option value="created_at">Plus anciennes</option>
          <option value="follow_up">Relance proche</option><option value="-priority">Priorité</option><option value="name">Nom A→Z</option>
        </select>
        <label style={{ display: "flex", gap: 6, alignItems: "center", fontSize: 10, whiteSpace: "nowrap" }}>
          <input type="checkbox" style={{ width: "auto", height: "auto" }} checked={overdue} onChange={(e) => { setOverdue(e.target.checked); setPage(1) }} />
          En retard
        </label>
      </div>
      <section className="admin-card table-card">
        {list.loading && !data ? <Loading /> : list.error && !data ? <ErrorBox message={list.error} onRetry={list.reload} /> : (
          <>
            <div className="table-wrap">
              <table>
                <thead><tr><th>Demandeur</th><th>Service</th><th>Date</th><th>Priorité</th><th>Statut</th><th>Assigné à</th><th>Relance</th><th></th></tr></thead>
                <tbody>
                  {data?.items.map((i) => (
                    <tr key={i.id} className={i.unread ? "unread" : ""}>
                      <td>
                        <button className="table-person" onClick={() => setSelected(i.id)}>
                          <span>{initials(i.name)}</span>
                          <p><b>{i.name}{i.isDemo && <em className="demo-tag">DÉMO</em>}</b><small>{i.company || ""} · {i.id}</small></p>
                        </button>
                      </td>
                      <td>{i.service}</td>
                      <td>{fmtDate(i.createdAt)}</td>
                      <td><span className={`priority ${i.priority.toLowerCase()}`}>{i.priority}</span></td>
                      <td><Badge>{i.status}</Badge></td>
                      <td>{i.assignee}</td>
                      <td className={i.overdue ? "overdue-flag" : ""}>{fmtDate(i.followUp)}</td>
                      <td><button className="row-open" aria-label="Ouvrir" onClick={() => setSelected(i.id)}><ChevronRight /></button></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {!data?.items.length && (
              <div className="empty"><Search /><h3>Aucune demande trouvée</h3><p>Essayez de modifier vos filtres de recherche.</p></div>
            )}
            <div className="pagination">
              <span>{data?.total ?? 0} résultat(s)</span>
              <div>
                <button disabled={page === 1} onClick={() => setPage((p) => p - 1)}>Précédent</button>
                <b>{page}</b>
                <button disabled={page >= (data?.pages ?? 1)} onClick={() => setPage((p) => p + 1)}>Suivant</button>
              </div>
            </div>
          </>
        )}
      </section>
      {selected && (
        <InquiryDrawer id={selected} team={team.data ?? []} canEdit={can("staff")} canDelete={can("admin")}
          onClose={closeDrawer} onChanged={list.reload} />
      )}
    </>
  )
}

function InquiryDrawer({ id, team, canEdit, canDelete, onClose, onChanged }: {
  id: string; team: TeamMember[]; canEdit: boolean; canDelete: boolean; onClose: () => void; onChanged: () => void
}) {
  const detail = useResource(() => api.inquiry(id), [id])
  const history = useResource(() => api.inquiryHistory(id), [id])
  const [note, setNote] = useState("")
  const [busy, setBusy] = useState(false)
  const inquiry = detail.data

  useEffect(() => { // opening a message marks it as read
    if (inquiry?.unread && canEdit) api.updateInquiry(id, { unread: false }).then(() => onChanged()).catch(() => {})
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [inquiry?.id])

  const patch = async (body: Record<string, unknown>) => {
    setBusy(true)
    try { detail.setData(await api.updateInquiry(id, body)); history.reload(); onChanged(); toast.ok("Modification enregistrée") }
    catch (e) { toast.err(e) } finally { setBusy(false) }
  }
  const addNote = async () => {
    if (!note.trim()) return
    setBusy(true)
    try { await api.addNote(id, note.trim()); setNote(""); detail.reload(); history.reload(); toast.ok("Note ajoutée") }
    catch (e) { toast.err(e) } finally { setBusy(false) }
  }
  const remove = async () => {
    if (!confirm("Supprimer définitivement cette demande ?")) return
    try { await api.deleteInquiry(id); toast.ok("Demande supprimée"); onChanged(); onClose() } catch (e) { toast.err(e) }
  }
  return (
    <div className="drawer-backdrop" onMouseDown={(e) => e.target === e.currentTarget && onClose()}>
      <aside className="detail-drawer">
        <div className="drawer-head">
          <div><p>{id}</p><h2>Détail de la demande</h2></div>
          <button onClick={onClose} aria-label="Fermer"><X /></button>
        </div>
        {detail.loading && !inquiry ? <Loading /> : !inquiry ? <ErrorBox message={detail.error} onRetry={detail.reload} /> : (
          <div className="drawer-body">
            <div className="client-block">
              <span>{initials(inquiry.name)}</span>
              <div><h3>{inquiry.name}</h3><p>{inquiry.company || ""}</p><small>{inquiry.email} · {inquiry.phone || ""}</small></div>
            </div>
            <div className="field-grid">
              <label>Statut
                <select disabled={!canEdit || busy} value={inquiry.status} onChange={(e) => patch({ status: e.target.value as InquiryStatus })}>
                  {[inquiry.status, ...TRANSITIONS[inquiry.status]].map((s) => <option key={s}>{s}</option>)}
                </select>
              </label>
              <label>Priorité
                <select disabled={!canEdit || busy} value={inquiry.priority} onChange={(e) => patch({ priority: e.target.value as Priority })}>
                  {priorities.map((s) => <option key={s}>{s}</option>)}
                </select>
              </label>
              <label>Responsable
                <select disabled={!canEdit || busy} value={inquiry.assigneeId ?? ""} onChange={(e) => patch({ assigneeId: e.target.value ? Number(e.target.value) : null })}>
                  <option value="">Non assigné</option>
                  {team.filter((t) => t.active || t.id === inquiry.assigneeId).map((t) => <option key={t.id} value={t.id}>{t.name}</option>)}
                </select>
              </label>
              <label>Relance
                <input type="date" disabled={!canEdit || busy} value={inquiry.followUp ?? ""} onChange={(e) => patch({ followUp: e.target.value || null })} />
              </label>
            </div>
            <section className="message-block">
              <p>MESSAGE CLIENT · reçu le {fmtDateTime(inquiry.createdAt)}</p>
              <h4>{inquiry.service}</h4>
              <span>{inquiry.message}</span>
            </section>
            <section className="notes">
              <p>NOTES INTERNES</p>
              {inquiry.notes.length ? inquiry.notes.map((n) => (
                <div key={n.id}><Activity /><span>{n.body}<small>{n.author} · {fmtDateTime(n.createdAt)}</small></span></div>
              )) : <em>Aucune note interne.</em>}
              {canEdit && (
                <form onSubmit={(e) => { e.preventDefault(); void addNote() }}>
                  <input value={note} maxLength={2000} onChange={(e) => setNote(e.target.value)} placeholder="Ajouter une note de suivi…" />
                  <button disabled={busy} aria-label="Ajouter la note"><Plus /></button>
                </form>
              )}
            </section>
            <section className="notes">
              <p>HISTORIQUE</p>
              {history.data?.length ? history.data.map((h: HistoryEvent) => (
                <div className="history-line" key={h.id}>
                  <b>{actionLabel[h.action] ?? h.action}</b> · {h.actor} · {fmtDateTime(h.createdAt)}
                  {h.action !== "note_added" && Object.entries(h.details).map(([k, v]) => (
                    <div key={k}>{k} : {Array.isArray(v) ? `${v[0] ?? ""} → ${v[1] ?? ""}` : String(v)}</div>
                  ))}
                </div>
              )) : <em>Aucun historique.</em>}
            </section>
          </div>
        )}
        <div className="drawer-footer">
          {canDelete ? <button className="danger-link" onClick={remove}><Trash2 />Supprimer</button> : <span />}
          <button className="admin-primary" onClick={onClose}><Check />Fermer</button>
        </div>
      </aside>
    </div>
  )
}
