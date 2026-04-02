import { ORDER_STATUS_CLASSES, ORDER_STATUS_LABELS } from '../../features/orders/orderStatus'
import type { OrderStatus } from '../../types/orders'

interface OrderCardProps {
  orderId: string
  status: OrderStatus
}

export function OrderCard({ orderId, status }: OrderCardProps) {
  return (
    <article>
      <div className="store-card__footer">
        <h3>Order #{orderId}</h3>
        <span className={`status-badge ${ORDER_STATUS_CLASSES[status]}`}>{ORDER_STATUS_LABELS[status]}</span>
      </div>
    </article>
  )
}
