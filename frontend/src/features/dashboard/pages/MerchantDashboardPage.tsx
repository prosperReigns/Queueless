import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { listMerchantOrdersRequest } from '../../../api/orders'
import { ORDER_STATUS_LABELS } from '../../orders/orderStatus'
import type { OrderStatus } from '../../../types/orders'

const MAX_LATEST_ORDERS_DISPLAY = 5

export function MerchantDashboardPage() {
  const ordersQuery = useQuery({
    queryKey: ['merchant-dashboard-orders'],
    queryFn: () => listMerchantOrdersRequest(),
    refetchInterval: 30000,
  })

  const orders = ordersQuery.data ?? []
  const countsByStatus = orders.reduce<Record<OrderStatus, number>>(
    (acc, order) => {
      acc[order.status] += 1
      return acc
    },
    { pending: 0, paid: 0, preparing: 0, ready: 0, completed: 0, cancelled: 0 },
  )

  const totals = {
    all: orders.length,
    pending: countsByStatus.pending,
    preparing: countsByStatus.preparing,
    ready: countsByStatus.ready,
    completed: countsByStatus.completed,
  }

  const latestOrders = orders.slice(0, MAX_LATEST_ORDERS_DISPLAY)

  return (
    <section className="page-container merchant-dashboard-page">
      <header className="page-header">
        <h1>Merchant Dashboard</h1>
        <p>Track fulfillment and act quickly on incoming orders.</p>
      </header>

      <div className="merchant-stats-grid">
        <article className="store-card">
          <h2>Total Orders</h2>
          <p className="merchant-stat-value">{totals.all}</p>
        </article>
        <article className="store-card">
          <h2>Pending</h2>
          <p className="merchant-stat-value">{totals.pending}</p>
        </article>
        <article className="store-card">
          <h2>Preparing</h2>
          <p className="merchant-stat-value">{totals.preparing}</p>
        </article>
        <article className="store-card">
          <h2>Ready</h2>
          <p className="merchant-stat-value">{totals.ready}</p>
        </article>
        <article className="store-card">
          <h2>Completed</h2>
          <p className="merchant-stat-value">{totals.completed}</p>
        </article>
      </div>

      <section className="store-card">
        <div className="store-card__footer">
          <h2>Latest Orders</h2>
          <Link to="/dashboard/merchant/orders" className="button-link">
            Manage Orders
          </Link>
        </div>

        {ordersQuery.isLoading ? <p>Loading orders...</p> : null}

        {!ordersQuery.isLoading && latestOrders.length === 0 ? (
          <p className="muted-text">No orders available yet.</p>
        ) : null}

        {!ordersQuery.isLoading && latestOrders.length > 0 ? (
          <div className="merchant-orders-list">
            {latestOrders.map((order) => (
              <article key={order.id} className="product-card">
                <div className="product-card__header">
                  <h3>Order #{order.id}</h3>
                  <span className="status-badge status-badge--muted">{ORDER_STATUS_LABELS[order.status]}</span>
                </div>
                <p className="muted-text">Total: ₦{Number(order.total_amount).toLocaleString()}</p>
                <p className="muted-text">Created: {new Date(order.created_at).toLocaleString()}</p>
              </article>
            ))}
          </div>
        ) : null}
      </section>
    </section>
  )
}
