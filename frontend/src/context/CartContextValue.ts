import { createContext } from 'react'
import type { Product } from '../api/stores'

export interface CartItem {
  productId: number
  storeId: number
  name: string
  price: number
  quantity: number
}

export interface AddToCartInput {
  product: Product
}

export interface CartContextValue {
  items: CartItem[]
  itemCount: number
  subtotal: number
  storeId: number | null
  addToCart: (input: AddToCartInput) => void
  updateQuantity: (productId: number, quantity: number) => void
  removeItem: (productId: number) => void
  clearCart: () => void
}

export const CartContext = createContext<CartContextValue | null>(null)
