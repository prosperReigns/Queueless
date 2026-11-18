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
  status: 'new' | 'accepted' | 'preparing' | 'ready'
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

export interface MembershipOption {
  id: string
  user_id: string
  branch_id: string | null
  role: string
  is_active: boolean
}
export interface MenuItemOption {
  id: string
  name: string
  description?: string | null
  price: string
  is_available: boolean
}
export interface MenuCategoryOption {
  id: string
  name: string
  items: MenuItemOption[]
}
export async function createBusinessRequest(payload: { name: string; business_type: 'independent' | 'franchise' }) {
  const { data } = await apiClient.post<BusinessOption>('/businesses', payload)
  return data
}
export async function createBranchRequest(businessId: string, payload: { name: string; city?: string; state?: string; country: string }) {
  const { data } = await apiClient.post<BranchOption>(`/businesses/${businessId}/branches`, payload)
  return data
}
export async function listMembershipsRequest(businessId: string) {
  const { data } = await apiClient.get<MembershipOption[]>(`/businesses/${businessId}/memberships`)
  return data
}
export async function createMembershipRequest(businessId: string, payload: { user_id: string; role: string; branch_id: string }) {
  const { data } = await apiClient.post<MembershipOption>(`/businesses/${businessId}/memberships`, payload)
  return data
}
export async function updateMembershipRequest(businessId: string, membershipId: string, isActive: boolean) {
  const { data } = await apiClient.patch<MembershipOption>(`/businesses/${businessId}/memberships/${membershipId}`, { is_active: isActive })
  return data
}
export async function createMenuCategoryRequest(businessId: string, payload: { name: string; description?: string }) {
  const { data } = await apiClient.post(`/businesses/${businessId}/menu/categories`, payload)
  return data
}
export async function createMenuItemRequest(businessId: string, payload: { name: string; category_id: string; base_price: number; description?: string }) {
  const { data } = await apiClient.post(`/businesses/${businessId}/menu/items`, payload)
  return data
}
export async function getPublicBranchMenuRequest(branchId: string) {
  const { data } = await apiClient.get<{ categories: MenuCategoryOption[] }>(`/public/branches/${branchId}/menu`)
  return data.categories
}
export async function updateBranchMenuItemRequest(branchId: string, itemId: string, payload: { is_available: boolean }) {
  const { data } = await apiClient.patch(`/branches/${branchId}/menu/items/${itemId}`, payload)
  return data
}

export interface PublicBranchMenu {
  business: { id: string; name: string; slug: string }
  branch: { id: string; name: string; city?: string | null; state?: string | null }
  categories: MenuCategoryOption[]
}
export async function listPublicBusinessBranchesRequest(slug: string) {
  const { data } = await apiClient.get<Array<{id:string;name:string;city?:string|null;state?:string|null}>>(`/public/businesses/${encodeURIComponent(slug)}/branches`)
  return data
}
export async function getPublicBranchMenuByIdRequest(branchId: string) {
  const { data } = await apiClient.get<PublicBranchMenu>(`/public/branches/${branchId}/menu`)
  return data
}
export async function getQrBranchMenuRequest(token: string) {
  const { data } = await apiClient.get<PublicBranchMenu>(`/public/branches/resolve/${token}/menu`)
  return data
}
export async function createBranchOrderRequest(payload: {
  branch_id?: string
  branch_qr_token?: string
  source: 'preorder' | 'onsite_qr'
  fulfillment_method: 'self_collection' | 'external_rider'
  customer_name: string
  customer_email: string
  customer_phone: string
  items: Array<{ menu_item_id: string; quantity: number }>
}) {
  const { data } = await apiClient.post<{id:number;guest_access_token?:string|null}>('/orders/branch', payload)
  return data
}
export async function initiateBranchPaymentRequest(orderId: number, callbackUrl: string, guestToken?: string) {
  const { data } = await apiClient.post<{authorization_url:string;reference:string}>('/payments/initiate', {
    order_id: orderId, callback_url: callbackUrl, guest_access_token: guestToken,
  })
  return data
}
export async function verifyBranchPaymentRequest(reference: string, guestToken?: string) {
  const { data } = await apiClient.post('/payments/verify', { reference, guest_access_token: guestToken })
  return data
}

export async function getBranchQrRequest(branchId: string) {
  const { data } = await apiClient.get<{branch_id:string;token:string;menu_url:string}>(`/branches/${branchId}/qr`)
  return data
}

export interface CustomerBranchOrder {
  id: number
  branch_id: string
  order_source: string | null
  fulfillment_method: string | null
  customer_name: string | null
  total_amount: string
  status: string
  created_at: string
  items: Array<{item_name:string;quantity:number;unit_price:string}>
}
export async function listMyBranchOrdersRequest() {
  const { data } = await apiClient.get<CustomerBranchOrder[]>('/customers/me/branch-orders')
  return data
}
