import { useQuery } from '@tanstack/react-query'
import axios from 'axios'
import { Link, useParams } from 'react-router-dom'
import { getOrderQrCodeRequest, getOrderRequest } from '../../../api/orders'

const POSITIVE_INTEGER_PATTERN = /^[1-9]\d*$/

export function OrderConfirmationPage() {
  const { orderId } = useParams<{ orderId: string }>()
  const isValidOrderId = typeof orderId === 'string' && POSITIVE_INTEGER_PATTERN.test(orderId)
  const parsedOrderId = isValidOrderId ? Number(orderId) : 0

  const orderQuery = useQuery({
    queryKey: ['order', parsedOrderId],
    queryFn: () => getOrderRequest(parsedOrderId),
    enabled: isValidOrderId,
  })

  const qrQuery = useQuery({
    queryKey: ['order-qr', parsedOrderId],
    queryFn: () => getOrderQrCodeRequest(parsedOrderId),
    enabled: isValidOrderId,
  })

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

  const qrErrorMessage = axios.isAxiosError<{ detail?: string }>(qrQuery.error)
    ? qrQuery.error.response?.data?.detail ?? 'Unable to load QR code.'
    : 'Unable to load QR code.'

  return (
    <section className="page-container">
      <header className="page-header">
        <h1>Order Confirmation</h1>
        <p>Track your order status and use the QR code for pickup.</p>
      </header>

      {orderQuery.isLoading ? <p>Loading order...</p> : null}
      {orderQuery.isError ? (
        <div className="inline-alert">
          <p>{orderErrorMessage}</p>
        </div>
      ) : null}

      {orderQuery.data ? (
        <article className="product-card">
          <h2>Order #{orderQuery.data.id}</h2>
          <p>
            <strong>Status:</strong> {orderQuery.data.status}
          </p>
          <p>
            <strong>Total:</strong> ₦{Number(orderQuery.data.total_amount).toLocaleString()}
          </p>
          <p className="muted-text">Created at: {new Date(orderQuery.data.created_at).toLocaleString()}</p>
        </article>
      ) : null}

      {qrQuery.isLoading ? <p>Loading QR code...</p> : null}
      {qrQuery.isError ? (
        <div className="inline-alert">
          <p>{qrErrorMessage}</p>
        </div>
      ) : null}

      {qrQuery.data ? (
        <article className="product-card qr-card">
          <h2>Pickup QR Code</h2>
          <img
            src={`data:image/png;base64,${qrQuery.data.qr_image_base64}`}
            alt={`QR code for order ${qrQuery.data.order_id}`}
            className="qr-image"
          />
        </article>
      ) : null}

      <div className="checkout-summary__actions">
        <Link to="/orders" className="button-link">
          View my orders
        </Link>
        <Link to="/" className="button-link">
          Continue shopping
        </Link>
      </div>
    </section>
  )
}
