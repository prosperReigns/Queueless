import { apiClient } from './client'

export interface BusinessOption {
  id: string
  name: string
  membership_role?: string | null
}
export interface BranchOption {
  id: string
  name: string
  city?: string | null
  state?: string | null
}
export interface KitchenTicket {
  ticket_id: number
  order_id: number
  branch_id: string
  status: 'NEW' | 'ACCEPTED' | 'PREPARING' | 'READY'
  order_source: string | null
  fulfillment_method: string | null
  scheduled_for: string | null
  customer_name: string | null
  customer_phone: string | null
  total_amount: string
  created_at: string | null
  items: Array<{ item_name: string; quantity: number; unit_price: string }>
}
export interface BranchOrder {
  id: number
  branch_id: string
  order_source: string | null
  fulfillment_method: string | null
  customer_name: string | null
  customer_phone: string | null
  total_amount: string
  status: string
  created_at: string
  items: Array<{ item_name: string; quantity: number; unit_price: string; line_total: number }>
}
export interface FulfillmentTracking {
  order_id: number
  order_status: string
  kitchen_status: string | null
  fulfillment_method: string | null
  fulfillment_status: string | null
  branch_id: string | null
  scheduled_for: string | null
  updated_at: string | null
}
export interface CollectionCredential {
  order_id: number
  fulfillment_method: string
  qr_payload: string
  pin: string
  expires_at: string
  single_use: boolean
}

export async function listBusinessesRequest() {
  const { data } = await apiClient.get<BusinessOption[]>('/businesses')
  return data
}
export async function listBranchesRequest(businessId: string) {
  const { data } = await apiClient.get<BranchOption[]>(`/businesses/${businessId}/branches`)
  return data
}
export async function getKitchenQueueRequest(branchId: string) {
  const { data } = await apiClient.get<{ branch_id: string; tickets: KitchenTicket[] }>(`/branches/${branchId}/kitchen/queue`)
  return data.tickets
}
export async function updateKitchenTicketRequest(ticketId: number, status: KitchenTicket['status']) {
  const { data } = await apiClient.patch<KitchenTicket>(`/kitchen/tickets/${ticketId}/status`, { status })
  return data
}
export async function listBranchOrdersRequest(branchId: string) {
  const { data } = await apiClient.get<BranchOrder[]>(`/branches/${branchId}/orders`)
  return data
}
export async function redeemCollectionRequest(branchId: string, payload: {
  credential_type: 'qr' | 'pin'
  credential: string
  handoff_name?: string
  handoff_phone?: string
}) {
  const { data } = await apiClient.post(`/branches/${branchId}/collection/redeem`, payload)
  return data
}
export async function getFulfillmentTrackingRequest(orderId: number, guestToken?: string) {
  const { data } = await apiClient.get<FulfillmentTracking>(`/orders/${orderId}/tracking`, {
    headers: guestToken ? { 'X-Guest-Access-Token': guestToken } : undefined,
  })
  return data
}
export async function issueCollectionCredentialRequest(orderId: number, guestToken?: string) {
  const { data } = await apiClient.post<CollectionCredential>(`/orders/${orderId}/collection-credential`, { rotate: false }, {
    headers: guestToken ? { 'X-Guest-Access-Token': guestToken } : undefined,
  })
  return data
}
