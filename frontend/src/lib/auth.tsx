import { useQueryClient } from '@tanstack/react-query'
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react'

import { api, getRefreshToken, onAuthChange, setTokens } from './api'
import type { Role, User } from './types'

const ROLE_ORDER: Record<Role, number> = {
  claimant: 0,
  agent: 1,
  supervisor: 2,
  admin: 3,
}

export function roleAtLeast(role: Role | undefined, minimum: Role): boolean {
  if (!role) return false
  return ROLE_ORDER[role] >= ROLE_ORDER[minimum]
}

interface AuthValue {
  user: User | null
  loading: boolean
  signIn: (email: string, password: string) => Promise<void>
  signOut: () => Promise<void>
  isStaff: boolean
  can: (minimum: Role) => boolean
}

const AuthContext = createContext<AuthValue | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)
  const queryClient = useQueryClient()

  // Restore the session from the stored refresh token on first paint.
  useEffect(() => {
    let cancelled = false

    async function restore() {
      if (!getRefreshToken()) {
        setLoading(false)
        return
      }
      try {
        const me = await api.get<User>('/users/me')
        if (!cancelled) setUser(me)
      } catch {
        setTokens(null, null)
      } finally {
        if (!cancelled) setLoading(false)
      }
    }

    void restore()
    return () => {
      cancelled = true
    }
  }, [])

  // A refresh failure anywhere in the app drops the session here too.
  useEffect(
    () =>
      onAuthChange((authenticated) => {
        if (!authenticated) setUser(null)
      }),
    [],
  )

  const signIn = useCallback(
    async (email: string, password: string) => {
      const tokens = await api.post<{
        access_token: string
        refresh_token: string
      }>('/auth/login', { email, password })
      setTokens(tokens.access_token, tokens.refresh_token)
      setUser(await api.get<User>('/users/me'))
    },
    [],
  )

  const signOut = useCallback(async () => {
    const refresh = getRefreshToken()
    try {
      if (refresh) await api.post('/auth/logout', { refresh_token: refresh })
    } catch {
      // Signing out locally must succeed even if the server call does not.
    }
    setTokens(null, null)
    setUser(null)
    queryClient.clear()
  }, [queryClient])

  const value = useMemo<AuthValue>(
    () => ({
      user,
      loading,
      signIn,
      signOut,
      isStaff: roleAtLeast(user?.role, 'agent'),
      can: (minimum: Role) => roleAtLeast(user?.role, minimum),
    }),
    [user, loading, signIn, signOut],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) throw new Error('useAuth must be used inside AuthProvider')
  return context
}
