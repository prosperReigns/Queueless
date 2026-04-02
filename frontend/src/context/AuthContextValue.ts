import { createContext } from 'react'
import type { AuthState, AuthUser, UserRole } from '../types/auth'

export interface AuthContextValue extends AuthState {
  role: UserRole | null
  isInitializing: boolean
  login: (email: string, password: string) => Promise<AuthUser>
  logout: () => void
}

export const AuthContext = createContext<AuthContextValue | null>(null)
