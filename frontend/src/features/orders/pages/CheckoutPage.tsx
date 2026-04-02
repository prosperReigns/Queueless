import { useMutation } from '@tanstack/react-query'
import axios from 'axios'
import { Link, Navigate, useNavigate } from 'react-router-dom'
import { createOrderRequest, initiatePaymentRequest } from '../../../api/orders'
import { useCart } from '../../../hooks/useCart'

export function CheckoutPage() {
  const navigate = useNavigate()
  const { items, storeId, subtotal, clearCart } = useCart()

  const checkoutMutation = useMutation({
    mutationFn: async () => {
      if (!storeId || items.length === 0) {
        throw new Error('Your cart is empty.')
      }

      const order = await createOrderRequest({
        store_id: storeId,
        items: items.map((item) => ({ product_id: item.productId, quantity: item.quantity })),
      })

      const callbackUrl = `${window.location.origin}/orders/${order.id}/confirmation`
      const payment = await initiatePaymentRequest(order.id, callbackUrl)

      return { orderId: order.id, paymentUrl: payment.authorization_url }
    },
    onSuccess: ({ orderId, paymentUrl }) => {
      clearCart()

      if (paymentUrl) {
        window.location.assign(paymentUrl)
        return
      }

      navigate(`/orders/${orderId}/confirmation`, { replace: true })
    },
  })

  if (!storeId || items.length === 0) {
    return <Navigate to="/cart" replace />
  }

  const errorMessage = axios.isAxiosError<{ detail?: string }>(checkoutMutation.error)
    ? checkoutMutation.error.response?.data?.detail ?? 'Unable to complete checkout.'
    : checkoutMutation.error instanceof Error
      ? checkoutMutation.error.message
      : 'Unable to complete checkout.'

  return (
    <section className="page-container">
      <header className="page-header">
        <h1>Checkout</h1>
        <p>Confirm your order and continue to payment.</p>
      </header>

      <div className="checkout-summary">
        <p>
          <strong>Items:</strong> {items.reduce((total, item) => total + item.quantity, 0)}
        </p>
        <p>
          <strong>Total:</strong> ₦{subtotal.toLocaleString()}
        </p>
      </div>

      {checkoutMutation.isError ? (
        <div className="inline-alert">
          <p>{errorMessage}</p>
        </div>
      ) : null}

      <div className="checkout-summary__actions">
        <Link to="/cart" className="button-link">
          Back to cart
        </Link>
        <button type="button" onClick={() => checkoutMutation.mutate()} disabled={checkoutMutation.isPending}>
          {checkoutMutation.isPending ? 'Processing...' : 'Place order & pay'}
        </button>
      </div>
    </section>
  )
}
