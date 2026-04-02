import { apiClient } from './client'
import type { OrderCreateRequest, OrderResponse, PaymentInitiateResponse, QRCodeResponse } from '../types/orders'

export async function createOrderRequest(payload: OrderCreateRequest): Promise<OrderResponse> {
  const { data } = await apiClient.post<OrderResponse>('/orders', payload)
  return data
}

export async function getOrderRequest(orderId: number): Promise<OrderResponse> {
  const { data } = await apiClient.get<OrderResponse>(`/orders/${orderId}`)
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
