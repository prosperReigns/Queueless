import { Link, Navigate, useNavigate } from 'react-router-dom'
import { useCart } from '../../../hooks/useCart'

export function CartPage() {
  const navigate = useNavigate()
  const { items, subtotal, updateQuantity, removeItem, clearCart, storeId } = useCart()

  if (items.length === 0) {
    return (
      <section className="page-container">
        <header className="page-header">
          <h1>Cart</h1>
          <p className="muted-text">Your cart is empty.</p>
        </header>
        <Link to="/" className="button-link">
          Browse stores
        </Link>
      </section>
    )
  }

  if (!storeId) {
    return <Navigate to="/" replace />
  }

  return (
    <section className="page-container">
      <header className="page-header">
        <h1>Cart</h1>
        <p>Review your items before checkout.</p>
      </header>

      <div className="cart-list">
        {items.map((item) => (
          <article key={item.productId} className="product-card">
            <div className="product-card__header">
              <h3>{item.name}</h3>
              <button type="button" onClick={() => removeItem(item.productId)}>
                Remove
              </button>
            </div>
            <p className="product-card__price">₦{(item.price * item.quantity).toLocaleString()}</p>
            <label>
              Quantity
              <input
                className="cart-quantity-input"
                type="number"
                min={1}
                value={item.quantity}
                onChange={(event) => updateQuantity(item.productId, Math.max(1, Number(event.target.value) || 1))}
              />
            </label>
          </article>
        ))}
      </div>

      <div className="checkout-summary">
        <p>
          <strong>Subtotal:</strong> ₦{subtotal.toLocaleString()}
        </p>
        <div className="checkout-summary__actions">
          <button type="button" onClick={clearCart}>
            Clear cart
          </button>
          <button type="button" onClick={() => navigate('/checkout')}>
            Proceed to checkout
          </button>
        </div>
      </div>
    </section>
  )
}
