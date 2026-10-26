import { api } from "../../services/api"
import { ErrorBox, Loading, PageHead, fmtDateTime, toast, useResource } from "../ui"
import { useNavigate } from "react-router-dom"

export function NotificationsPage() {
  const nav = useNavigate()
  const n = useResource(() => api.notifications(), [], 30000)
  if (n.loading && !n.data) return <Loading />
  if (n.error && !n.data) return <ErrorBox message={n.error} onRetry={n.reload} />
  return (
    <>
      <PageHead eyebrow="ACTIVITÉ" title="Notifications" description="Nouvelles demandes, relances et alertes qui vous concernent."
        action={<button className="admin-secondary" onClick={() => api.markAllRead().then(n.reload).catch(toast.err)}>Tout marquer comme lu</button>} />
      <section className="admin-card">
        {n.data?.items.length ? n.data.items.map((x) => (
          <button key={x.id} className={`notif-item ${x.read ? "" : "unread"}`}
            onClick={async () => { if (!x.read) await api.markRead(x.id).catch(() => {}); if (x.link) nav(x.link); else n.reload() }}>
            <b>{x.title}</b><span>{x.body}</span><small>{fmtDateTime(x.createdAt)}</small>
          </button>
        )) : <div className="empty"><h3>Aucune notification</h3><p>Vous êtes à jour.</p></div>}
      </section>
    </>
  )
}
