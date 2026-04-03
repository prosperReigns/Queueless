import { useEffect } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import axios from 'axios'
import { OrderCard } from '../../../components/cards/OrderCard'
import { listOrdersRequest, updateOrderStatusRequest } from '../../../api/orders'
import { useAuth } from '../../../hooks/useAuth'
import { getStoredAccessToken } from '../../../context/authStorage'
import { subscribeToOrderUpdates } from '../../../services/websocket'
import type { OrderStatus } from '../../../types/orders'
import { NEXT_STATUS_OPTIONS } from '../orderStatus'
import { ORDER_STATUS_LABELS } from '../orderStatus'

export function OrdersManagementPage() {
  const queryClient = useQueryClient()
  const { user } = useAuth()

  const merchantOrdersQuery = useQuery({
    queryKey: ['orders', user?.id],
    queryFn: () => listOrdersRequest(),
    enabled: Boolean(user?.id),
    refetchInterval: 30000,
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

  const updateStatusMutation = useMutation({
    mutationFn: ({ orderId, status }: { orderId: number; status: OrderStatus }) =>
      updateOrderStatusRequest(orderId, { status }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['orders', user?.id] })
    },
  })

  const errorMessage = axios.isAxiosError<{ detail?: string }>(merchantOrdersQuery.error)
    ? merchantOrdersQuery.error.response?.data?.detail ?? 'Unable to load orders.'
    : 'Unable to load orders.'

  const updateErrorMessage = axios.isAxiosError<{ detail?: string }>(updateStatusMutation.error)
    ? updateStatusMutation.error.response?.data?.detail ?? 'Unable to update order status.'
    : 'Unable to update order status.'

  return (
    <section className="page-container merchant-orders-page">
      <header className="page-header">
        <h1>Orders Management</h1>
        <p>Review incoming orders and move each order through fulfillment.</p>
      </header>

      <div className="checkout-summary__actions">
        <button type="button" onClick={() => void merchantOrdersQuery.refetch()} disabled={merchantOrdersQuery.isFetching}>
          {merchantOrdersQuery.isFetching ? 'Refreshing...' : 'Refresh orders'}
        </button>
      </div>

      {merchantOrdersQuery.isLoading ? <p>Loading orders...</p> : null}

      {merchantOrdersQuery.isError ? (
        <div className="inline-alert">
          <p>{errorMessage}</p>
          <button type="button" onClick={() => void merchantOrdersQuery.refetch()} disabled={merchantOrdersQuery.isFetching}>
            {merchantOrdersQuery.isFetching ? 'Retrying...' : 'Try again'}
          </button>
        </div>
      ) : null}

      {updateStatusMutation.isError ? (
        <div className="inline-alert">
          <p>{updateErrorMessage}</p>
          <button type="button" onClick={() => updateStatusMutation.reset()}>
            Dismiss
          </button>
        </div>
      ) : null}

      {!merchantOrdersQuery.isLoading && !merchantOrdersQuery.isError && merchantOrdersQuery.data?.length === 0 ? (
        <p className="muted-text">No merchant orders yet.</p>
      ) : null}

      {!merchantOrdersQuery.isLoading && !merchantOrdersQuery.isError && merchantOrdersQuery.data ? (
        <div className="merchant-orders-list">
          {merchantOrdersQuery.data.map((order) => {
            const nextStatuses = NEXT_STATUS_OPTIONS[order.status]
            return (
              <article key={order.id} className="store-card">
                <OrderCard orderId={String(order.id)} status={order.status} />
                <p className="muted-text">Created: {new Date(order.created_at).toLocaleString()}</p>
                <p className="muted-text">Items: {order.items.length}</p>
                <p className="muted-text">Total: ₦{Number(order.total_amount).toLocaleString()}</p>

                <div className="checkout-summary__actions">
                  {nextStatuses.length > 0 ? (
                    nextStatuses.map((status) => (
                      <button
                        key={status}
                        type="button"
                        onClick={() => updateStatusMutation.mutate({ orderId: order.id, status })}
                        disabled={updateStatusMutation.isPending}
                      >
                        Mark as {ORDER_STATUS_LABELS[status]}
                      </button>
                    ))
                  ) : (
                    <span className="muted-text">No further status changes</span>
                  )}
                </div>
              </article>
            )
          })}
        </div>
      ) : null}
    </section>
  )
}
