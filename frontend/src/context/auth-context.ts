import { createContext } from 'react'
import type { AuthState, AuthUser, UserRole } from '../types/auth'

export interface AuthContextValue extends AuthState {
  role: UserRole | null
  login: (user: AuthUser, token: string) => void
  logout: () => void
}

export const AuthContext = createContext<AuthContextValue | null>(null)
