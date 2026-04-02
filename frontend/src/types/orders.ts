export interface OrderItemCreate {
  product_id: number
  quantity: number
}

export type OrderStatus = 'pending' | 'paid' | 'preparing' | 'ready' | 'completed' | 'cancelled'

export interface OrderCreateRequest {
  store_id: number
  items: OrderItemCreate[]
}

export interface OrderItemResponse {
  id: number
  order_id: number
  product_id: number
  quantity: number
  price: string
}

export interface OrderResponse {
  id: number
  user_id: string
  store_id: number
  total_amount: string
  status: OrderStatus
  payment_reference: string
  created_at: string
  items: OrderItemResponse[]
}

export interface OrderStatusUpdateRequest {
  status: OrderStatus
}

export interface PaymentResponse {
  id: number
  order_id: number
  reference: string
  status: string
  amount: string
  provider: string
  created_at: string
}

export interface PaymentInitiateResponse {
  payment: PaymentResponse
  authorization_url: string
  access_code: string
  reference: string
}

export interface QRCodeResponse {
  order_id: number
  qr_data: string
  qr_image_base64: string
}
