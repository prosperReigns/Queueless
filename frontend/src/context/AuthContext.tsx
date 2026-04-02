import { useEffect, useMemo, useState } from 'react'
import { AuthContext } from './AuthContextValue'
import type { AuthState, AuthUser } from '../types/auth'
import { loginRequest, meRequest } from '../api/auth'
import { clearStoredAuth, getInitialAuthState, storeToken } from './authStorage'

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [state, setState] = useState<AuthState>(() => getInitialAuthState())
  const [isAuthenticating, setIsAuthenticating] = useState(false)

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
      isInitializing: Boolean(state.token && !state.user),
      login: async (email: string, password: string): Promise<AuthUser> => {
        if (isAuthenticating) {
          throw new Error('Please wait for the current login attempt to complete')
        }

        setIsAuthenticating(true)

        try {
          const tokenPair = await loginRequest({ email, password })
          storeToken(tokenPair.access_token)
          const user = await meRequest()
          setState({ user, token: tokenPair.access_token })
          return user
        } catch (error) {
          clearStoredAuth()
          setState({ user: null, token: null })
          throw error
        } finally {
          setIsAuthenticating(false)
        }
      },
      logout: () => {
        clearStoredAuth()
        setState({ user: null, token: null })
      },
    }),
    [isAuthenticating, state],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}
