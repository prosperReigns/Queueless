import { useEffect, useMemo, useState } from 'react'
import { AuthContext } from './AuthContextValue'
import type { AuthState, AuthUser } from '../types/auth'
import { loginRequest, meRequest } from '../api/auth'
import { clearStoredAuth, getInitialAuthState, storeToken } from './authStorage'

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [state, setState] = useState<AuthState>(() => getInitialAuthState())
  const [isInitializing, setIsInitializing] = useState(() => Boolean(getInitialAuthState().token))

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
          setIsInitializing(false)
        }
      } catch {
        if (!cancelled) {
          clearStoredAuth()
          setState({ user: null, token: null })
          setIsInitializing(false)
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
      isInitializing,
      login: async (email: string, password: string): Promise<AuthUser> => {
        const tokenPair = await loginRequest({ email, password })
        storeToken(tokenPair.access_token)
        const user = await meRequest()
        setState({ user, token: tokenPair.access_token })
        setIsInitializing(false)
        return user
      },
      logout: () => {
        clearStoredAuth()
        setState({ user: null, token: null })
        setIsInitializing(false)
      },
    }),
    [isInitializing, state],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}
