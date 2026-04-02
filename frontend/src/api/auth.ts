import { apiClient } from './client'
import type { AuthUser, UserRole } from '../types/auth'

interface LoginRequest {
  email: string
  password: string
}

interface RegisterRequest {
  email: string
  password: string
  role?: UserRole
}

interface LoginResponse {
  access_token: string
  refresh_token: string
  token_type: string
}

interface MeResponse {
  id: string
  email: string
  role: string
}

const toUserRole = (role: string): UserRole => {
  const normalized = role.toUpperCase()

  if (normalized === 'CUSTOMER' || normalized === 'MERCHANT' || normalized === 'ADMIN') {
    return normalized
  }

  return 'CUSTOMER'
}

const toAuthUser = (payload: MeResponse): AuthUser => ({
  id: payload.id,
  name: payload.email,
  role: toUserRole(payload.role),
})

export async function loginRequest(payload: LoginRequest): Promise<LoginResponse> {
  const { data } = await apiClient.post<LoginResponse>('/auth/login', payload)
  return data
}

export async function registerRequest(payload: RegisterRequest): Promise<void> {
  await apiClient.post('/auth/register', {
    ...payload,
    role: payload.role?.toLowerCase(),
  })
}

export async function meRequest(accessToken?: string): Promise<AuthUser> {
  const { data } = await apiClient.get<MeResponse>('/auth/me', {
    headers: accessToken ? { Authorization: `Bearer ${accessToken}` } : undefined,
  })
  return toAuthUser(data)
}
