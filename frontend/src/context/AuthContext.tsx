import { useMemo, useState } from 'react'
import { AuthContext } from './AuthContextValue'
import type { AuthState, AuthUser } from '../types/auth'
import { clearStoredAuth, getInitialAuthState, storeAuth } from './authStorage'

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [state, setState] = useState<AuthState>(() => getInitialAuthState())

  const value = useMemo(
    () => ({
      ...state,
      role: state.user?.role ?? null,
      login: (user: AuthUser, token: string) => {
        storeAuth(user, token)
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
