import { useMemo, useState } from 'react'
import { CartContext } from './CartContextValue'
import type { CartContextValue, CartItem } from './CartContextValue'

interface StoredCart {
  items: CartItem[]
}

const CART_STORAGE_KEY = 'queueless_cart'

const getInitialCartItems = (): CartItem[] => {
  try {
    const parsed = JSON.parse(localStorage.getItem(CART_STORAGE_KEY) ?? 'null') as StoredCart | null
    if (!parsed?.items || !Array.isArray(parsed.items)) {
      return []
    }

    return parsed.items.filter((item) =>
      Number.isInteger(item.productId) &&
      item.productId > 0 &&
      Number.isInteger(item.storeId) &&
      item.storeId > 0 &&
      typeof item.name === 'string' &&
      Number.isFinite(item.price) &&
      item.price >= 0 &&
      Number.isInteger(item.quantity) &&
      item.quantity > 0,
    )
  } catch {
    return []
  }
}

const persistItems = (items: CartItem[]) => {
  localStorage.setItem(CART_STORAGE_KEY, JSON.stringify({ items }))
}

export function CartProvider({ children }: { children: React.ReactNode }) {
  const [items, setItems] = useState<CartItem[]>(() => getInitialCartItems())

  const value = useMemo<CartContextValue>(() => {
    const itemCount = items.reduce((total, item) => total + item.quantity, 0)
    const subtotal = items.reduce((total, item) => total + item.price * item.quantity, 0)
    const storeId = items.length > 0 ? items[0].storeId : null

    return {
      items,
      itemCount,
      subtotal,
      storeId,
      addToCart: ({ product }) => {
        setItems((current) => {
          const normalizedCurrent = current.filter((item) => item.storeId === product.store_id)
          const existing = normalizedCurrent.find((item) => item.productId === product.id)
          let next: CartItem[]

          if (existing) {
            next = normalizedCurrent.map((item) =>
              item.productId === product.id ? { ...item, quantity: item.quantity + 1 } : item,
            )
          } else {
            next = [
              ...normalizedCurrent,
              {
                productId: product.id,
                storeId: product.store_id,
                name: product.name,
                price: product.price,
                quantity: 1,
              },
            ]
          }

          persistItems(next)
          return next
        })
      },
      updateQuantity: (productId, quantity) => {
        setItems((current) => {
          const next = current
            .map((item) => (item.productId === productId ? { ...item, quantity } : item))
            .filter((item) => item.quantity > 0)
          persistItems(next)
          return next
        })
      },
      removeItem: (productId) => {
        setItems((current) => {
          const next = current.filter((item) => item.productId !== productId)
          persistItems(next)
          return next
        })
      },
      clearCart: () => {
        setItems([])
        persistItems([])
      },
    }
  }, [items])

  return <CartContext.Provider value={value}>{children}</CartContext.Provider>
}
