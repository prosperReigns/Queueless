import { apiClient } from './client'
import type { Store } from './stores'
import type { AuthUser } from '../types/auth'

export interface AdminUser extends AuthUser {
  is_active: boolean
  created_at: string
}

export async function listAdminUsersRequest(): Promise<AdminUser[]> {
  const { data } = await apiClient.get<AdminUser[]>('/admin/users')
  return data
}

export async function setAdminUserActiveRequest(userId: string, isActive: boolean): Promise<AdminUser> {
  const { data } = await apiClient.patch<AdminUser>(`/admin/users/${userId}/active`, {
    is_active: isActive,
  })
  return data
}

export async function listAdminStoresRequest(): Promise<Store[]> {
  const { data } = await apiClient.get<Store[]>('/admin/stores')
  return data
}

export async function setAdminStoreActiveRequest(storeId: number, isActive: boolean): Promise<Store> {
  const { data } = await apiClient.patch<Store>(`/admin/stores/${storeId}/active`, {
    is_active: isActive,
  })
  return data
}
