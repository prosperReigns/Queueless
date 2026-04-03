import type { UserRole } from './auth'
import type { OrderStatus } from './orders'

export const USER_ROLES = ['CUSTOMER', 'MERCHANT', 'ADMIN'] as const satisfies readonly UserRole[]
export const ACTIVE_ORDER_STATUSES: ReadonlySet<OrderStatus> = new Set([
  'pending',
  'paid',
  'preparing',
  'ready',
])
