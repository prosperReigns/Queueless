import type { OrderStatus } from '../../types/orders'

export interface OrderStatusOption {
  value: OrderStatus
  label: string
  className: string
}

export const ORDER_STATUS_OPTIONS: OrderStatusOption[] = [
  { value: 'pending', label: 'Pending', className: 'status-badge--pending' },
  { value: 'paid', label: 'Paid', className: 'status-badge--paid' },
  { value: 'preparing', label: 'Preparing', className: 'status-badge--preparing' },
  { value: 'ready', label: 'Ready', className: 'status-badge--ready' },
  { value: 'completed', label: 'Completed', className: 'status-badge--completed' },
  { value: 'cancelled', label: 'Cancelled', className: 'status-badge--cancelled' },
]

export const ORDER_STATUS_LABELS: Record<OrderStatus, string> = ORDER_STATUS_OPTIONS.reduce(
  (acc, option) => {
    acc[option.value] = option.label
    return acc
  },
  {} as Record<OrderStatus, string>,
)

export const ORDER_STATUS_CLASSES: Record<OrderStatus, string> = ORDER_STATUS_OPTIONS.reduce(
  (acc, option) => {
    acc[option.value] = option.className
    return acc
  },
  {} as Record<OrderStatus, string>,
)

export const NEXT_STATUS_OPTIONS: Record<OrderStatus, OrderStatus[]> = {
  pending: ['paid'],
  paid: ['preparing'],
  preparing: ['ready'],
  ready: ['completed'],
  completed: [],
  cancelled: [],
}
