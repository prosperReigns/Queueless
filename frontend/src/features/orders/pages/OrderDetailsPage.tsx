import { useEffect, useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import axios from 'axios'
import { Link, useParams } from 'react-router-dom'
import { getOrderRequest } from '../../../api/orders'
import { OrderCard } from '../../../components/cards/OrderCard'
import { getStoredAccessToken } from '../../../context/authStorage'
import { subscribeToOrderUpdates } from '../../../services/websocket'

const POSITIVE_INTEGER_PATTERN = /^[1-9]\d*$/

export function OrderDetailsPage() {
  const queryClient = useQueryClient()
  const { orderId } = useParams<{ orderId: string }>()
  const isValidOrderId = typeof orderId === 'string' && POSITIVE_INTEGER_PATTERN.test(orderId)
  const parsedOrderId = isValidOrderId ? Number(orderId) : 0
  const [isRealtimeConnected, setIsRealtimeConnected] = useState(false)

  const orderQuery = useQuery({
    queryKey: ['order', parsedOrderId],
    queryFn: () => getOrderRequest(parsedOrderId),
    enabled: isValidOrderId,
    refetchInterval: isRealtimeConnected ? false : 15000,
  })

  useEffect(() => {
    const token = getStoredAccessToken()
    if (!token || !isValidOrderId) {
      return undefined
    }

    return subscribeToOrderUpdates({
      token,
      onOpen: () => {
        setIsRealtimeConnected(true)
      },
      onOrderEvent: (event) => {
        if (event.type === 'order_status_update' && event.order_id === parsedOrderId) {
          void queryClient.invalidateQueries({ queryKey: ['order', parsedOrderId] })
        }
      },
      onError: () => {
        setIsRealtimeConnected(false)
        void queryClient.invalidateQueries({ queryKey: ['order', parsedOrderId] })
      },
      onClose: () => {
        setIsRealtimeConnected(false)
      },
    })
  }, [isValidOrderId, parsedOrderId, queryClient])

  if (!isValidOrderId) {
    return (
      <section className="page-container">
        <h1>Invalid order</h1>
        <p className="muted-text">The order identifier is invalid.</p>
        <Link to="/orders" className="button-link">
          Back to orders
        </Link>
      </section>
    )
  }

  const orderErrorMessage = axios.isAxiosError<{ detail?: string }>(orderQuery.error)
    ? orderQuery.error.response?.data?.detail ?? 'Unable to load order details.'
    : 'Unable to load order details.'

  return (
    <section className="page-container">
      <header className="page-header">
        <h1>Order Details</h1>
        <p>Track your order progress and latest status updates.</p>
      </header>

      {orderQuery.isLoading ? <p>Loading order details...</p> : null}
      {orderQuery.isError ? (
        <div className="inline-alert">
          <p>{orderErrorMessage}</p>
          <button type="button" onClick={() => void orderQuery.refetch()} disabled={orderQuery.isFetching}>
            {orderQuery.isFetching ? 'Retrying...' : 'Try again'}
          </button>
        </div>
      ) : null}

      {!orderQuery.isLoading && !orderQuery.isError && orderQuery.data ? (
        <article className="store-card">
          <OrderCard orderId={String(orderQuery.data.id)} status={orderQuery.data.status} />
          <p className="muted-text">Created: {new Date(orderQuery.data.created_at).toLocaleString()}</p>
          <p className="muted-text">Items: {orderQuery.data.items.length}</p>
          <p className="muted-text">Total: ₦{Number(orderQuery.data.total_amount).toLocaleString()}</p>
        </article>
      ) : null}

      <p className="muted-text">
        Tracking updates: {isRealtimeConnected ? 'Live via WebSocket' : 'Polling fallback (every 15s)'}
      </p>

      <div className="checkout-summary__actions">
        <Link to={`/orders/${parsedOrderId}/confirmation`} className="button-link">
          View pickup QR
        </Link>
        <Link to="/orders" className="button-link">
          Back to my orders
        </Link>
      </div>
    </section>
  )
}
