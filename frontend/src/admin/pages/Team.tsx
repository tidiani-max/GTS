import { useState, type FormEvent } from "react"
import { Plus, X } from "lucide-react"
import { api } from "../../services/api"
import { useAuth } from "../../services/auth"
import type { Role } from "../../types"
import { ErrorBox, Loading, PageHead, fmtDateTime, initials, roleLabels, toast, useResource } from "../ui"

export function Team() {
  const { can, user } = useAuth()
  const list = useResource(() => api.users(), [])
  const [creating, setCreating] = useState(false)
  const [resetFor, setResetFor] = useState<number | null>(null)
  const manage = can("super_admin")
  if (list.loading && !list.data) return <Loading />
  if (list.error && !list.data) return <ErrorBox message={list.error} onRetry={list.reload} />
  const update = async (id: number, body: Record<string, unknown>) => {
    try { await api.updateUser(id, body); toast.ok("Utilisateur mis à jour"); list.reload() } catch (e) { toast.err(e) }
  }
  return (
    <>
      <PageHead eyebrow="ADMINISTRATION" title="Équipe & accès" description="Utilisateurs de l’administration, rôles et accès (gérés par les super-administrateurs)."
        action={manage ? <button className="admin-primary" onClick={() => setCreating(true)}><Plus />Inviter</button> : undefined} />
      <section className="admin-card table-card">
        <div className="table-wrap">
          <table>
            <thead><tr><th>Utilisateur</th><th>Rôle d’accès</th><th>Fonction</th><th>Dernière connexion</th><th>État</th>{manage && <th></th>}</tr></thead>
            <tbody>
              {list.data?.map((m) => (
                <tr key={m.id}>
                  <td><div className="table-person"><span>{initials(m.name)}</span>
                    <p><b>{m.name}{m.isDemo && <em className="demo-tag">DÉMO</em>}</b><small>{m.email}</small></p></div></td>
                  <td>
                    <select disabled={!manage || m.id === user?.id} value={m.role} onChange={(e) => update(m.id, { role: e.target.value as Role })}>
                      {Object.entries(roleLabels).map(([v, l]) => <option key={v} value={v}>{l}</option>)}
                    </select>
                  </td>
                  <td>{m.jobTitle}</td>
                  <td>{fmtDateTime(m.lastLoginAt)}</td>
                  <td>
                    <label className="switch">
                      <input type="checkbox" disabled={!manage || m.id === user?.id} checked={m.active} onChange={(e) => update(m.id, { active: e.target.checked })} />
                      <i />
                    </label>
                  </td>
                  {manage && <td><button className="admin-secondary" onClick={() => setResetFor(m.id)}>Mot de passe</button></td>}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
      {creating && <UserModal onClose={() => setCreating(false)} onDone={() => { setCreating(false); list.reload() }} />}
      {resetFor !== null && <ResetModal id={resetFor} onClose={() => setResetFor(null)} />}
    </>
  )
}

function UserModal({ onClose, onDone }: { onClose: () => void; onDone: () => void }) {
  const [f, setF] = useState({ name: "", email: "", jobTitle: "Collaborateur", role: "staff" as Role, password: "" })
  const [busy, setBusy] = useState(false)
  const submit = async (e: FormEvent) => {
    e.preventDefault(); setBusy(true)
    try { await api.createUser(f); toast.ok("Utilisateur créé"); onDone() } catch (err) { toast.err(err) } finally { setBusy(false) }
  }
  return (
    <div className="modal-backdrop">
      <form className="admin-modal" onSubmit={submit}>
        <div className="drawer-head"><div><p>NOUVEAU</p><h2>Inviter un utilisateur</h2></div><button type="button" onClick={onClose}><X /></button></div>
        <div className="modal-fields">
          <label>Nom complet<input required minLength={2} value={f.name} onChange={(e) => setF({ ...f, name: e.target.value })} /></label>
          <label>Email<input required type="email" value={f.email} onChange={(e) => setF({ ...f, email: e.target.value })} /></label>
          <label>Fonction<input value={f.jobTitle} onChange={(e) => setF({ ...f, jobTitle: e.target.value })} /></label>
          <label>Rôle d’accès
            <select value={f.role} onChange={(e) => setF({ ...f, role: e.target.value as Role })}>
              {Object.entries(roleLabels).map(([v, l]) => <option key={v} value={v}>{l}</option>)}
            </select>
          </label>
          <label className="full">Mot de passe initial (10 caractères min., majuscules, minuscules, chiffre)
            <input required minLength={10} type="password" autoComplete="new-password" value={f.password} onChange={(e) => setF({ ...f, password: e.target.value })} />
          </label>
        </div>
        <div className="modal-actions">
          <button type="button" className="admin-secondary" onClick={onClose}>Annuler</button>
          <button className="admin-primary" disabled={busy}>Créer</button>
        </div>
      </form>
    </div>
  )
}

function ResetModal({ id, onClose }: { id: number; onClose: () => void }) {
  const [pw, setPw] = useState("")
  const submit = async (e: FormEvent) => {
    e.preventDefault()
    try { await api.updateUser(id, { password: pw }); toast.ok("Mot de passe réinitialisé (sessions fermées)"); onClose() } catch (err) { toast.err(err) }
  }
  return (
    <div className="modal-backdrop">
      <form className="admin-modal" onSubmit={submit}>
        <div className="drawer-head"><div><p>SÉCURITÉ</p><h2>Nouveau mot de passe</h2></div><button type="button" onClick={onClose}><X /></button></div>
        <div className="modal-fields"><label className="full">Mot de passe
          <input required minLength={10} type="password" autoComplete="new-password" value={pw} onChange={(e) => setPw(e.target.value)} /></label></div>
        <div className="modal-actions">
          <button type="button" className="admin-secondary" onClick={onClose}>Annuler</button>
          <button className="admin-primary">Réinitialiser</button>
        </div>
      </form>
    </div>
  )
}
