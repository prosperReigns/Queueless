import type { UserRole } from '../types/auth'

export const DASHBOARD_PATH_BY_ROLE: Record<UserRole, string> = {
  CUSTOMER: '/dashboard/customer',
  MERCHANT: '/dashboard/merchant',
  ADMIN: '/dashboard/admin',
}
