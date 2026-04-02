interface OrderCardProps {
  orderId: string
  status: string
}

export function OrderCard({ orderId, status }: OrderCardProps) {
  return (
    <article>
      <h3>Order {orderId}</h3>
      <p>Status: {status}</p>
    </article>
  )
}
