import { useEffect, useMemo, useState } from 'react'
import { AuthContext } from './AuthContextValue'
import type { AuthState, AuthUser } from '../types/auth'
import { meRequest } from '../api/auth'
import { clearStoredAuth, getInitialAuthState, storeToken } from './authStorage'

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [state, setState] = useState<AuthState>(() => getInitialAuthState())

  useEffect(() => {
    if (!state.token || state.user) {
      return
    }

    let cancelled = false

    void (async () => {
      try {
        const user = await meRequest()
        if (!cancelled) {
          setState((currentState) => ({ ...currentState, user }))
        }
      } catch {
        if (!cancelled) {
          clearStoredAuth()
          setState({ user: null, token: null })
        }
      }
    })()

    return () => {
      cancelled = true
    }
  }, [state.token, state.user])

  const value = useMemo(
    () => ({
      ...state,
      role: state.user?.role ?? null,
      login: (user: AuthUser, token: string) => {
        storeToken(token)
        setState({ user, token })
      },
      logout: () => {
        clearStoredAuth()
        setState({ user: null, token: null })
      },
    }),
    [state],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}
