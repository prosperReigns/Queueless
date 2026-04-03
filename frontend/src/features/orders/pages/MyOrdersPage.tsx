import { useEffect } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import axios from 'axios'
import { Link } from 'react-router-dom'
import { listOrdersRequest } from '../../../api/orders'
import { OrderCard } from '../../../components/cards/OrderCard'
import { getStoredAccessToken } from '../../../context/authStorage'
import { useAuth } from '../../../hooks/useAuth'
import { subscribeToOrderUpdates } from '../../../services/websocket'

export function MyOrdersPage() {
  const queryClient = useQueryClient()
  const { user } = useAuth()
  const POLLING_INTERVAL_MS = 15000

  const ordersQuery = useQuery({
    queryKey: ['orders', user?.id],
    queryFn: () => listOrdersRequest(),
    enabled: Boolean(user?.id),
    refetchInterval: POLLING_INTERVAL_MS,
  })

  useEffect(() => {
    const token = getStoredAccessToken()
    if (!token || !user?.id) {
      return undefined
    }

    return subscribeToOrderUpdates({
      token,
      onOrderEvent: () => {
        void queryClient.invalidateQueries({ queryKey: ['orders', user.id] })
      },
      onError: () => {
        void queryClient.invalidateQueries({ queryKey: ['orders', user.id] })
      },
    })
  }, [queryClient, user?.id])

  const errorMessage = axios.isAxiosError<{ detail?: string }>(ordersQuery.error)
    ? ordersQuery.error.response?.data?.detail ?? 'Unable to load orders.'
    : 'Unable to load orders.'

  return (
    <section className="page-container">
      <header className="page-header">
        <h1>My Orders</h1>
        <p>Review your recent orders and track their status.</p>
      </header>

      <div className="checkout-summary__actions">
        <button type="button" onClick={() => void ordersQuery.refetch()} disabled={ordersQuery.isFetching}>
          {ordersQuery.isFetching ? 'Refreshing...' : 'Refresh orders'}
        </button>
      </div>

      {ordersQuery.isLoading ? <p>Loading orders...</p> : null}
      {!ordersQuery.isLoading && ordersQuery.isFetching ? <p className="muted-text">Updating your orders...</p> : null}

      {ordersQuery.isError ? (
        <div className="inline-alert">
          <p>{errorMessage}</p>
          <button type="button" onClick={() => void ordersQuery.refetch()} disabled={ordersQuery.isFetching}>
            {ordersQuery.isFetching ? 'Retrying...' : 'Try again'}
          </button>
        </div>
      ) : null}

      {!ordersQuery.isLoading && !ordersQuery.isError ? (
        <p className="muted-text">Status updates are received in real-time and poll every 15s as fallback.</p>
      ) : null}

      {!ordersQuery.isLoading && !ordersQuery.isError && ordersQuery.data?.length === 0 ? (
        <p className="muted-text">You have no orders yet.</p>
      ) : null}

      {!ordersQuery.isLoading && !ordersQuery.isError && ordersQuery.data ? (
        <div className="merchant-orders-list">
          {ordersQuery.data.map((order) => (
            <article key={order.id} className="store-card">
              <OrderCard orderId={String(order.id)} status={order.status} />
              <p className="muted-text">Created: {new Date(order.created_at).toLocaleString()}</p>
              <p className="muted-text">Items: {order.items.length}</p>
              <p className="muted-text">Total: ₦{Number(order.total_amount).toLocaleString()}</p>
              <div className="checkout-summary__actions">
                <Link to={`/orders/${order.id}`} className="button-link">
                  View details
                </Link>
              </div>
            </article>
          ))}
        </div>
      ) : null}
    </section>
  )
}
