import type {
  AppNotification, AutomationConfig, AutomationStatus, Company, EmailRow, HistoryEvent, Inquiry, JobRun, Note,
  Overview, Page, Project, Service, TeamMember,
} from "../types"

/**
 * Backend base URL. Set VITE_API_BASE_URL at build/dev time:
 *   - local dev:     http://localhost:8000/api/v1   (see .env.development)
 *   - docker/nginx:  /api/v1                        (same origin, proxied)
 */
export const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || "/api/v1").replace(/\/$/, "")

export class ApiError extends Error {
  constructor(
    public status: number,
    public code: string,
    message: string,
    public details?: { field?: string; message?: string }[] | null,
  ) {
    super(message)
  }
}

// Access token lives in memory only (never localStorage). The refresh token is an httpOnly cookie.
let accessToken: string | null = null
let refreshing: Promise<boolean> | null = null
let onSessionExpired: () => void = () => {}
export const setSessionExpiredHandler = (fn: () => void) => (onSessionExpired = fn)
export const setAccessToken = (t: string | null) => (accessToken = t)

async function parseError(res: Response): Promise<ApiError> {
  try {
    const body = await res.json()
    const e = body.error
    return new ApiError(res.status, e?.code ?? "error", e?.message ?? res.statusText, e?.details)
  } catch {
    return new ApiError(res.status, "error", res.statusText || "Erreur réseau")
  }
}

export async function refreshSession(): Promise<boolean> {
  refreshing ??= (async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/auth/refresh`, { method: "POST", credentials: "include" })
      if (!res.ok) return false
      accessToken = (await res.json()).accessToken
      return true
    } catch {
      return false
    } finally {
      setTimeout(() => (refreshing = null), 0)
    }
  })()
  return refreshing
}

async function raw(path: string, init: RequestInit = {}, retry = true): Promise<Response> {
  const headers = new Headers(init.headers)
  if (init.body && !headers.has("Content-Type")) headers.set("Content-Type", "application/json")
  if (accessToken) headers.set("Authorization", `Bearer ${accessToken}`)
  let res: Response
  try {
    res = await fetch(`${API_BASE_URL}${path}`, { ...init, headers, credentials: "include" })
  } catch {
    throw new ApiError(0, "network", "Serveur injoignable. Vérifiez votre connexion.")
  }
  if (res.status === 401 && retry && !path.startsWith("/auth/login") && !path.startsWith("/auth/refresh")) {
    if (await refreshSession()) return raw(path, init, false)
    accessToken = null
    onSessionExpired()
  }
  if (!res.ok) throw await parseError(res)
  return res
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await raw(path, init)
  return res.status === 204 ? (undefined as T) : res.json()
}

const qs = (params: Record<string, unknown> = {}) => {
  const u = new URLSearchParams()
  Object.entries(params).forEach(([k, v]) => v !== undefined && v !== null && v !== "" && u.set(k, String(v)))
  const s = u.toString()
  return s ? `?${s}` : ""
}
const json = (method: string, body?: unknown): RequestInit => ({ method, body: body === undefined ? undefined : JSON.stringify(body) })

async function download(path: string, filename: string) {
  const blob = await (await raw(path)).blob()
  const a = document.createElement("a")
  a.href = URL.createObjectURL(blob)
  a.download = filename
  a.click()
  URL.revokeObjectURL(a.href)
}

export type InquiryQuery = {
  q?: string; status?: string; priority?: string; assigneeId?: string; unread?: boolean; overdue?: boolean
  sort?: string; page?: number; pageSize?: number
}
// Backend query params are snake_case for filters; map from camelCase here.
const inquiryParams = (p: InquiryQuery) => ({
  q: p.q, status: p.status, priority: p.priority, assignee_id: p.assigneeId, unread: p.unread,
  overdue: p.overdue, sort: p.sort, page: p.page, pageSize: p.pageSize,
})

export const api = {
  // auth
  async login(email: string, password: string) {
    const r = await request<{ accessToken: string; user: TeamMember }>("/auth/login", json("POST", { email, password }))
    accessToken = r.accessToken
    return r.user
  },
  async logout() {
    try {
      await request("/auth/logout", json("POST"))
    } finally {
      accessToken = null
    }
  },
  me: () => request<TeamMember>("/auth/me"),
  changePassword: (currentPassword: string, newPassword: string) =>
    request<void>("/auth/change-password", json("POST", { currentPassword, newPassword })),
  updateProfile: (b: Partial<Pick<TeamMember, "name" | "email" | "jobTitle" | "prefs">>) =>
    request<TeamMember>("/me", json("PATCH", b)),

  // public
  submitContact: (b: { name: string; email: string; message: string; service: string; website?: string }) =>
    request<{ reference: string; message: string }>("/public/contact", json("POST", b)),
  publicServices: () => request<{ id: string; title: string; description: string }[]>("/public/services"),
  publicCompany: () => request<Company>("/public/company"),

  // inquiries
  inquiries: (p: InquiryQuery) => request<Page<Inquiry>>(`/inquiries${qs(inquiryParams(p))}`),
  inquiry: (id: string) => request<Inquiry>(`/inquiries/${id}`),
  updateInquiry: (id: string, b: Record<string, unknown>) => request<Inquiry>(`/inquiries/${id}`, json("PATCH", b)),
  addNote: (id: string, body: string) => request<Note>(`/inquiries/${id}/notes`, json("POST", { body })),
  inquiryHistory: (id: string) => request<HistoryEvent[]>(`/inquiries/${id}/history`),
  deleteInquiry: (id: string) => request<void>(`/inquiries/${id}`, json("DELETE")),
  exportInquiries: (p: InquiryQuery) =>
    download(`/inquiries/export.csv${qs(inquiryParams({ ...p, page: undefined, pageSize: undefined }))}`, "demandes-gst.csv"),

  // projects / services / users
  projects: (p: { q?: string; status?: string; page?: number; pageSize?: number } = {}) =>
    request<Page<Project>>(`/projects${qs({ ...p, pageSize: p.pageSize ?? 100 })}`),
  saveProject: (id: string | null, b: Record<string, unknown>) =>
    id ? request<Project>(`/projects/${id}`, json("PATCH", b)) : request<Project>("/projects", json("POST", b)),
  deleteProject: (id: string) => request<void>(`/projects/${id}`, json("DELETE")),
  exportProjects: () => download("/projects/export.csv", "projets-gst.csv"),
  services: () => request<Service[]>("/services"),
  saveService: (id: string | null, b: Partial<Service>) =>
    id ? request<Service>(`/services/${id}`, json("PATCH", b)) : request<Service>("/services", json("POST", b)),
  deleteService: (id: string) => request<void>(`/services/${id}`, json("DELETE")),
  users: () => request<TeamMember[]>("/users"),
  createUser: (b: Record<string, unknown>) => request<TeamMember>("/users", json("POST", b)),
  updateUser: (id: number, b: Record<string, unknown>) => request<TeamMember>(`/users/${id}`, json("PATCH", b)),

  // notifications, settings, reports
  notifications: () => request<{ items: AppNotification[]; unreadCount: number }>("/notifications"),
  markRead: (id: number) => request<void>(`/notifications/${id}/read`, json("POST")),
  markAllRead: () => request<void>("/notifications/read-all", json("POST")),
  company: () => request<Company>("/settings/company"),
  saveCompany: (b: Company) => request<Company>("/settings/company", json("PUT", b)),
  overview: (range: string) => request<Overview>(`/reports/overview${qs({ range })}`),
  exportReport: (range: string) => download(`/reports/overview.csv${qs({ range })}`, `rapport-gst-${range}.csv`),
  audit: (page = 1) => request<Page<HistoryEvent>>(`/audit${qs({ page, pageSize: 20 })}`),

  // automation
  automationStatus: () => request<AutomationStatus>("/automation/status"),
  saveAutomation: (b: AutomationConfig) => request<AutomationConfig>("/automation/config", json("PUT", b)),
  runJob: (name: string, dryRun: boolean) => request<JobRun>(`/automation/jobs/${name}/run${qs({ dry_run: dryRun })}`, json("POST")),
  jobRuns: (page = 1) => request<Page<JobRun>>(`/automation/runs${qs({ page, pageSize: 10 })}`),
  emails: (page = 1) => request<Page<EmailRow>>(`/automation/emails${qs({ page, pageSize: 10 })}`),
}

export const errorMessage = (e: unknown) =>
  e instanceof ApiError ? (e.details?.length && e.code === "validation_error" ? `${e.message} ${e.details.map((d) => d.message).join(" ; ")}` : e.message) : "Une erreur est survenue."
