import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react"
import { api, refreshSession, setSessionExpiredHandler } from "./api"
import type { Role, TeamMember } from "../types"

const LEVEL: Record<Role, number> = { readonly: 0, staff: 1, admin: 2, super_admin: 3 }

interface AuthState {
  user: TeamMember | null
  loading: boolean
  expired: boolean
  login: (email: string, password: string) => Promise<void>
  logout: () => Promise<void>
  can: (min: Role) => boolean
  setUser: (u: TeamMember) => void
}
const Ctx = createContext<AuthState>(null!)
export const useAuth = () => useContext(Ctx)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<TeamMember | null>(null)
  const [loading, setLoading] = useState(true)
  const [expired, setExpired] = useState(false)

  useEffect(() => {
    setSessionExpiredHandler(() => { setUser(null); setExpired(true) })
    // Restore the session from the httpOnly refresh cookie (if any).
    ;(async () => {
      if (await refreshSession()) {
        try { setUser(await api.me()) } catch { /* not logged in */ }
      }
      setLoading(false)
    })()
  }, [])

  const login = useCallback(async (email: string, password: string) => {
    setUser(await api.login(email, password))
    setExpired(false)
  }, [])
  const logout = useCallback(async () => {
    try { await api.logout() } catch { /* cookie cleared best-effort */ }
    setUser(null)
  }, [])
  const value = useMemo<AuthState>(
    () => ({ user, loading, expired, login, logout, setUser, can: (min) => !!user && LEVEL[user.role] >= LEVEL[min] }),
    [user, loading, expired, login, logout],
  )
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>
}
