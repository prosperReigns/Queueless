export const ORDER_UPDATES_WEBSOCKET_URL = import.meta.env.VITE_WS_BASE_URL ?? 'ws://localhost:8000/api/v1/ws/orders'

export type OrderSocketEventType = 'new_order' | 'order_status_update'

export interface OrderSocketEvent {
  type: OrderSocketEventType
  order_id: number
  store_id: number
  customer_id: string
  status: string
  total_amount: string
  created_at: string | null
}

export function createOrderUpdatesSocket(url: string) {
  return new WebSocket(url)
}

export function buildOrderUpdatesSocketUrl(token: string) {
  return `${ORDER_UPDATES_WEBSOCKET_URL}?token=${encodeURIComponent(token)}`
}

export function subscribeToOrderUpdates(options: {
  token: string
  onOrderEvent: (event: OrderSocketEvent) => void
  onError?: () => void
}) {
  const socket = createOrderUpdatesSocket(buildOrderUpdatesSocketUrl(options.token))

  socket.onmessage = (event) => {
    try {
      const payload = JSON.parse(event.data) as Partial<OrderSocketEvent>
      if (
        (payload.type === 'new_order' || payload.type === 'order_status_update') &&
        typeof payload.order_id === 'number'
      ) {
        options.onOrderEvent(payload as OrderSocketEvent)
      }
    } catch {
      // Ignore malformed websocket messages.
    }
  }

  socket.onerror = () => {
    options.onError?.()
  }

  return () => {
    socket.close()
  }
}
