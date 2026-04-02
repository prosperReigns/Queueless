import { apiClient } from './client'
import type {
  OrderCreateRequest,
  OrderResponse,
  OrderStatusUpdateRequest,
  PaymentInitiateResponse,
  QRCodeResponse,
} from '../types/orders'

const sortOrdersByCreatedAtDesc = (orders: OrderResponse[]) =>
  [...orders].sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())

export async function createOrderRequest(payload: OrderCreateRequest): Promise<OrderResponse> {
  const { data } = await apiClient.post<OrderResponse>('/orders', payload)
  return data
}

export async function getOrderRequest(orderId: number): Promise<OrderResponse> {
  const { data } = await apiClient.get<OrderResponse>(`/orders/${orderId}`)
  return data
}

export async function listMerchantOrdersRequest(maxFallbackOrderId = 25): Promise<OrderResponse[]> {
  try {
    const { data } = await apiClient.get<OrderResponse[]>('/orders')
    return sortOrdersByCreatedAtDesc(data)
  } catch {
    const orderIds = Array.from({ length: maxFallbackOrderId }, (_, index) => index + 1)
    const responses = await Promise.allSettled(orderIds.map((id) => getOrderRequest(id)))
    const orders = responses
      .filter((result): result is PromiseFulfilledResult<OrderResponse> => result.status === 'fulfilled')
      .map((result) => result.value)
    return sortOrdersByCreatedAtDesc(orders)
  }
}

export async function updateOrderStatusRequest(
  orderId: number,
  payload: OrderStatusUpdateRequest,
): Promise<OrderResponse> {
  const { data } = await apiClient.patch<OrderResponse>(`/orders/${orderId}/status`, payload)
  return data
}

export async function initiatePaymentRequest(orderId: number, callbackUrl?: string): Promise<PaymentInitiateResponse> {
  const { data } = await apiClient.post<PaymentInitiateResponse>('/payments/initiate', {
    order_id: orderId,
    callback_url: callbackUrl,
  })
  return data
}

export async function getOrderQrCodeRequest(orderId: number): Promise<QRCodeResponse> {
  const { data } = await apiClient.get<QRCodeResponse>(`/qr-codes/orders/${orderId}`)
  return data
}
