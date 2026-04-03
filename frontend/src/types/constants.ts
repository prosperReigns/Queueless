import type { UserRole } from './auth'
import type { OrderStatus } from './orders'

export const USER_ROLES = ['CUSTOMER', 'MERCHANT', 'ADMIN'] as const satisfies readonly UserRole[]
export const ACTIVE_ORDER_STATUSES = ['pending', 'paid', 'preparing', 'ready'] as const satisfies readonly OrderStatus[]
