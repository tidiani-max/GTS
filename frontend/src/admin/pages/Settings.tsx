import { useEffect, useState, type FormEvent } from "react"
import { Bell, BriefcaseBusiness, Check, CircleUserRound, ShieldCheck } from "lucide-react"
import { api } from "../../services/api"
import { useAuth } from "../../services/auth"
import type { Company } from "../../types"
import { ErrorBox, Loading, PageHead, toast, useResource } from "../ui"

const PREFS: [string, string][] = [
  ["new_inquiry", "Nouvelle demande client"], ["project_status", "Changement de statut projet"],
  ["follow_up_due", "Échéance de suivi"], ["monthly_report", "Résumé périodique"],
]

export function AdminSettings() {
  const { user, setUser, can } = useAuth()
  const company = useResource(() => api.company(), [])
  const [profile, setProfile] = useState({ name: user?.name ?? "", email: user?.email ?? "", jobTitle: user?.jobTitle ?? "" })
  const [prefs, setPrefs] = useState<Record<string, boolean>>({ new_inquiry: true, project_status: true, follow_up_due: true, monthly_report: true, ...user?.prefs })
  const [co, setCo] = useState<Company | null>(null)
  const [pw, setPw] = useState({ current: "", next: "" })
  const [saving, setSaving] = useState(false)
  useEffect(() => { if (company.data) setCo(company.data) }, [company.data])
  if (company.loading && !co) return <Loading />
  if (company.error && !co) return <ErrorBox message={company.error} onRetry={company.reload} />
  const editCompany = can("admin")
  const save = async (e: FormEvent) => {
    e.preventDefault(); setSaving(true)
    try {
      setUser(await api.updateProfile({ ...profile, prefs }))
      if (editCompany && co) await api.saveCompany(co)
      toast.ok("Paramètres enregistrés")
    } catch (err) { toast.err(err) } finally { setSaving(false) }
  }
  const changePw = async (e: FormEvent) => {
    e.preventDefault()
    try { await api.changePassword(pw.current, pw.next); setPw({ current: "", next: "" }); toast.ok("Mot de passe modifié") } catch (err) { toast.err(err) }
  }
  return (
    <>
      <PageHead eyebrow="CONFIGURATION" title="Paramètres" description="Profil, notifications et informations de l’entreprise." />
      <form className="settings-grid" onSubmit={save}>
        <section className="admin-card settings-card">
          <h2><CircleUserRound />Profil administrateur</h2>
          <label>Nom complet<input required minLength={2} value={profile.name} onChange={(e) => setProfile({ ...profile, name: e.target.value })} /></label>
          <label>Email<input required type="email" value={profile.email} onChange={(e) => setProfile({ ...profile, email: e.target.value })} /></label>
          <label>Fonction<input value={profile.jobTitle} onChange={(e) => setProfile({ ...profile, jobTitle: e.target.value })} /></label>
        </section>
        <section className="admin-card settings-card">
          <h2><BriefcaseBusiness />Informations GST</h2>
          <label>Nom de l’entreprise<input disabled={!editCompany} value={co?.name ?? ""} onChange={(e) => co && setCo({ ...co, name: e.target.value })} /></label>
          <label>Email public<input disabled={!editCompany} value={co?.email ?? ""} onChange={(e) => co && setCo({ ...co, email: e.target.value })} /></label>
          <label>Adresse<textarea disabled={!editCompany} value={co?.address ?? ""} onChange={(e) => co && setCo({ ...co, address: e.target.value })} /></label>
        </section>
        <section className="admin-card settings-card full">
          <h2><Bell />Notifications (in-app et email)</h2>
          {PREFS.map(([key, label]) => (
            <label className="setting-toggle" key={key}>
              <span><b>{label}</b><small>Préférence personnelle, appliquée par le serveur</small></span>
              <span className="switch"><input type="checkbox" checked={!!prefs[key]} onChange={(e) => setPrefs({ ...prefs, [key]: e.target.checked })} /><i /></span>
            </label>
          ))}
        </section>
        <div className="settings-actions">
          <button className="admin-primary" disabled={saving}>{saving ? "Enregistrement…" : "Enregistrer les paramètres"}</button>
        </div>
      </form>
      <form className="settings-grid" style={{ marginTop: 16 }} onSubmit={changePw}>
        <section className="admin-card settings-card full">
          <h2><ShieldCheck />Changer mon mot de passe</h2>
          <label>Mot de passe actuel<input type="password" autoComplete="current-password" required value={pw.current} onChange={(e) => setPw({ ...pw, current: e.target.value })} /></label>
          <label>Nouveau mot de passe (10 caractères min.)<input type="password" autoComplete="new-password" required minLength={10} value={pw.next} onChange={(e) => setPw({ ...pw, next: e.target.value })} /></label>
        </section>
        <div className="settings-actions"><button className="admin-primary"><Check size={15} /> Modifier le mot de passe</button></div>
      </form>
    </>
  )
}
