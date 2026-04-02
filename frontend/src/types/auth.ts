export type UserRole = 'CUSTOMER' | 'MERCHANT' | 'ADMIN'

export interface AuthUser {
  id: string
  name: string
  role: UserRole
}

export interface AuthState {
  user: AuthUser | null
  token: string | null
}
