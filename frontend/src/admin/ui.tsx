import { useCallback, useEffect, useRef, useState, type ReactNode } from "react"
import { errorMessage } from "../services/api"

const statusColors: Record<string, string> = {
  Nouveau: "blue", "À étudier": "amber", "En cours": "purple", Résolu: "green", Rejeté: "red",
  Planifié: "amber", Suspendu: "red", Terminé: "green", success: "green", failed: "red", running: "blue",
  sent: "green", pending: "amber", skipped: "", Actif: "green", Inactif: "red",
}
export const statuses = ["Nouveau", "À étudier", "En cours", "Résolu", "Rejeté"] as const
export const priorities = ["Basse", "Normale", "Haute", "Urgente"] as const
// Mirrors the server-side workflow (backend enforces it too).
export const TRANSITIONS: Record<string, string[]> = {
  Nouveau: ["À étudier", "En cours", "Résolu", "Rejeté"],
  "À étudier": ["Nouveau", "En cours", "Résolu", "Rejeté"],
  "En cours": ["Nouveau", "À étudier", "Résolu", "Rejeté"],
  Résolu: ["En cours", "À étudier"],
  Rejeté: ["À étudier", "En cours"],
}
export const roleLabels: Record<string, string> = {
  super_admin: "Super-administrateur", admin: "Administrateur", staff: "Collaborateur", readonly: "Lecture seule",
}

export function Badge({ children }: { children: ReactNode }) {
  return <span className={`badge ${statusColors[String(children)] || ""}`}>{children}</span>
}
export function Loading() {
  return <div className="loading"><span />Chargement des données…</div>
}
export function ErrorBox({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div className="empty" role="alert">
      <h3>Impossible de charger les données</h3>
      <p>{message}</p>
      {onRetry && <button className="admin-secondary" style={{ marginTop: 12 }} onClick={onRetry}>Réessayer</button>}
    </div>
  )
}
export function PageHead({ eyebrow, title, description, action }: {
  eyebrow: string; title: string; description: string; action?: ReactNode
}) {
  return (
    <div className="page-head">
      <div><p>{eyebrow}</p><h1>{title}</h1><span>{description}</span></div>
      {action}
    </div>
  )
}
export const initials = (name: string) => name.split(" ").map((x) => x[0]).join("").slice(0, 2).toUpperCase()
export const fmtDate = (d?: string | null) => (d ? new Date(d).toLocaleDateString("fr-FR") : "")
export const fmtDateTime = (d?: string | null) =>
  d ? new Date(d).toLocaleString("fr-FR", { dateStyle: "short", timeStyle: "short" }) : ""

/** Fetch + loading/error state + manual reload + optional polling (keeps browsers in sync). */
export function useResource<T>(fn: () => Promise<T>, deps: unknown[], pollMs = 0) {
  const [data, setData] = useState<T | null>(null)
  const [error, setError] = useState("")
  const [loading, setLoading] = useState(true)
  const fnRef = useRef(fn)
  fnRef.current = fn
  const load = useCallback(async (silent = false) => {
    if (!silent) setLoading(true)
    try { setData(await fnRef.current()); setError("") } catch (e) { setError(errorMessage(e)) } finally { setLoading(false) }
  }, [])
  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => { void load() }, deps)
  useEffect(() => {
    if (!pollMs) return
    const t = setInterval(() => { if (!document.hidden) void load(true) }, pollMs)
    const onFocus = () => void load(true)
    window.addEventListener("focus", onFocus)
    return () => { clearInterval(t); window.removeEventListener("focus", onFocus) }
  }, [pollMs, load])
  return { data, error, loading, reload: () => load(), setData }
}

// ---- tiny toast system ----
type Toast = { id: number; kind: "ok" | "err"; text: string }
let push: (t: Omit<Toast, "id">) => void = () => {}
export const toast = { ok: (text: string) => push({ kind: "ok", text }), err: (e: unknown) => push({ kind: "err", text: errorMessage(e) }) }
export function Toasts() {
  const [items, setItems] = useState<Toast[]>([])
  useEffect(() => {
    push = (t) => {
      const id = Date.now() + Math.random()
      setItems((x) => [...x, { ...t, id }])
      setTimeout(() => setItems((x) => x.filter((i) => i.id !== id)), 4500)
    }
    return () => { push = () => {} }
  }, [])
  return (
    <div className="toasts" aria-live="polite">
      {items.map((t) => <div key={t.id} className={`toast ${t.kind}`}>{t.text}</div>)}
    </div>
  )
}
