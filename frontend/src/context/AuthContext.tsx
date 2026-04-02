import { createContext, useMemo, useState } from 'react'
import type { AuthState, AuthUser, UserRole } from '../types/auth'

interface AuthContextValue extends AuthState {
  role: UserRole | null
  login: (user: AuthUser, token: string) => void
  logout: () => void
}

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

export const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [state, setState] = useState<AuthState>(() => getInitialState())

  const value = useMemo<AuthContextValue>(
    () => ({
      ...state,
      role: state.user?.role ?? null,
      login: (user, token) => {
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
