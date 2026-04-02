import { useMemo, useState } from 'react'
import { AuthContext } from './auth-context'
import type { AuthState, AuthUser } from '../types/auth'

const TOKEN_KEY = 'queueless_token'
const USER_KEY = 'queueless_user'

const getInitialState = (): AuthState => {
  const token = localStorage.getItem(TOKEN_KEY)
  const savedUser = localStorage.getItem(USER_KEY)

  if (!token || !savedUser) {
    return { user: null, token: null }
  }

  try {
    return { user: JSON.parse(savedUser) as AuthUser, token }
  } catch {
    localStorage.removeItem(TOKEN_KEY)
    localStorage.removeItem(USER_KEY)
    return { user: null, token: null }
  }
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [state, setState] = useState<AuthState>(() => getInitialState())

  const value = useMemo(
    () => ({
      ...state,
      role: state.user?.role ?? null,
      login: (user: AuthUser, token: string) => {
        localStorage.setItem(TOKEN_KEY, token)
        localStorage.setItem(USER_KEY, JSON.stringify(user))
        setState({ user, token })
      },
      logout: () => {
        localStorage.removeItem(TOKEN_KEY)
        localStorage.removeItem(USER_KEY)
        setState({ user: null, token: null })
      },
    }),
    [state],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}
