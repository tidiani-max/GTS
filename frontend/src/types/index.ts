export type InquiryStatus = "Nouveau" | "À étudier" | "En cours" | "Résolu" | "Rejeté"
export type Priority = "Basse" | "Normale" | "Haute" | "Urgente"
export type ProjectStatus = "Planifié" | "En cours" | "Suspendu" | "Terminé"
export type Role = "readonly" | "staff" | "admin" | "super_admin"

export interface Note {
  id: number
  body: string
  author: string
  createdAt: string
}

export interface Inquiry {
  id: string
  name: string
  company: string
  email: string
  phone: string
  service: string
  message: string
  status: InquiryStatus
  priority: Priority
  assignee: string
  assigneeId: number | null
  createdAt: string
  followUp: string | null
  unread: boolean
  overdue: boolean
  isDemo: boolean
  notes: Note[]
}

export interface HistoryEvent {
  id: number
  action: string
  actor: string
  details: Record<string, unknown>
  createdAt: string
}

export interface Project {
  id: string
  name: string
  client: string
  service: string
  status: ProjectStatus
  progress: number
  deadline: string | null
  lead: string
  leadId: number | null
  isDemo: boolean
}

export interface Service {
  id: string
  title: string
  description: string
  active: boolean
}

export interface TeamMember {
  id: number
  name: string
  email: string
  role: Role
  jobTitle: string
  active: boolean
  isDemo: boolean
  lastLoginAt: string | null
  prefs: Record<string, boolean>
}

export interface Page<T> {
  items: T[]
  total: number
  page: number
  pageSize: number
  pages: number
}

export interface AppNotification {
  id: number
  kind: string
  title: string
  body: string
  link: string
  read: boolean
  createdAt: string
}

export interface Company {
  name: string
  email: string
  address: string
  phone: string
}

export interface Overview {
  range: string
  kpis: {
    totalInquiries: number
    inquiriesInRange: number
    toTreat: number
    unread: number
    overdue: number
    activeProjects: number
    completedProjects: number
    totalProjects: number
    resolutionRate: number
    avgResolutionDays: number | null
    last30Days: number
    previous30Days: number
    trendPct: number | null
  }
  trend: { month: string; demandes: number; resolues: number }[]
  byStatus: { name: string; value: number }[]
  byPriority: { name: string; value: number }[]
  byService: { name: string; value: number }[]
  projectsByStatus: { name: string; value: number }[]
}

export interface JobRun {
  id: number
  job: string
  trigger: string
  dryRun: boolean
  status: string
  startedAt: string
  finishedAt: string | null
  summary: Record<string, unknown>
  error: string
}

export interface AutomationConfig {
  remindersEnabled: boolean
  remindersEveryMinutes: number
  reminderLeadDays: number
  reminderMinGapHours: number
  maxReminders: number
  overdueEnabled: boolean
  overdueEveryMinutes: number
  newInquiryEnabled: boolean
  notifyAssignee: boolean
  summaryEnabled: boolean
  summaryWeekday: number
  summaryHour: number
  cleanupEnabled: boolean
  retentionDays: number
  extraRecipients: string[]
  dryRun: boolean
}

export interface AutomationStatus {
  config: AutomationConfig
  emailMode: string
  outbox: Record<string, number>
  jobs: {
    name: string
    label: string
    nextDue: string | null
    lastRun: JobRun | null
    failedRuns: number
  }[]
}

export interface EmailRow {
  id: number
  toEmail: string
  subject: string
  status: string
  attempts: number
  lastError: string
  createdAt: string
  sentAt: string | null
}
