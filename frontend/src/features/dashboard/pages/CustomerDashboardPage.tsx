import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import axios from 'axios'
import { listOrdersRequest } from '../../../api/orders'
import { useAuth } from '../../../hooks/useAuth'
import { ACTIVE_ORDER_STATUSES } from '../../../types/constants'

const RECENT_ORDERS_LIMIT = 5

export function CustomerDashboardPage() {
  const { user } = useAuth()
  const ordersQuery = useQuery({
    queryKey: ['customer-dashboard-orders', user?.id],
    queryFn: listOrdersRequest,
    enabled: Boolean(user?.id),
    refetchInterval: 30000,
  })

  const orders = ordersQuery.data ?? []
  const activeOrdersCount = orders.filter((order) => ACTIVE_ORDER_STATUSES.has(order.status)).length
  const completedOrdersCount = orders.filter((order) => order.status === 'completed').length
  const recentOrders = orders.slice(0, RECENT_ORDERS_LIMIT)

  const ordersErrorMessage = axios.isAxiosError<{ detail?: string }>(ordersQuery.error)
    ? ordersQuery.error.response?.data?.detail ?? 'Unable to load dashboard data.'
    : 'Unable to load dashboard data.'

  return (
    <section className="page-container">
      <header className="page-header">
        <h1>Customer Dashboard</h1>
        <p>Get a quick view of your order activity and next steps.</p>
      </header>

      {ordersQuery.isLoading ? <p>Loading dashboard...</p> : null}

      {ordersQuery.isError ? (
        <div className="inline-alert">
          <p>{ordersErrorMessage}</p>
          <button type="button" onClick={() => void ordersQuery.refetch()} disabled={ordersQuery.isFetching}>
            {ordersQuery.isFetching ? 'Retrying...' : 'Try again'}
          </button>
        </div>
      ) : null}

      {!ordersQuery.isLoading && !ordersQuery.isError ? (
        <>
          <div className="merchant-stats-grid customer-stats-grid">
            <article className="store-card">
              <h2>Total Orders</h2>
              <p className="merchant-stat-value">{orders.length}</p>
            </article>
            <article className="store-card">
              <h2>Active Orders</h2>
              <p className="merchant-stat-value">{activeOrdersCount}</p>
            </article>
            <article className="store-card">
              <h2>Completed</h2>
              <p className="merchant-stat-value">{completedOrdersCount}</p>
            </article>
          </div>

          <section className="store-card">
            <div className="store-card__footer">
              <h2>Recent Orders</h2>
              <Link to="/orders" className="button-link">
                View all
              </Link>
            </div>
            {recentOrders.length === 0 ? (
              <p className="muted-text">You have no orders yet. Browse stores to place your first order.</p>
            ) : (
              <div className="merchant-orders-list">
                {recentOrders.map((order) => (
                  <article key={order.id} className="product-card">
                    <div className="product-card__header">
                      <h3>Order #{order.id}</h3>
                      <span className="status-badge status-badge--muted">{order.status}</span>
                    </div>
                    <p className="muted-text">Total: ₦{Number(order.total_amount).toLocaleString()}</p>
                    <p className="muted-text">Created: {new Date(order.created_at).toLocaleString()}</p>
                    <div className="checkout-summary__actions">
                      <Link to={`/orders/${order.id}`} className="button-link">
                        View details
                      </Link>
                    </div>
                  </article>
                ))}
              </div>
            )}
          </section>
        </>
      ) : null}
    </section>
  )
}
