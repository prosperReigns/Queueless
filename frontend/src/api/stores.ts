import { apiClient } from './client'

export interface Store {
  id: number
  name: string
  description: string | null
  location: string | null
  is_active: boolean
  owner_id: string
  created_at: string
}

export interface Product {
  id: number
  store_id: number
  name: string
  description: string | null
  price: number
  is_available: boolean
  image_url: string | null
}

export interface ProductCreateRequest {
  store_id: number
  name: string
  description: string | null
  price: number
  is_available: boolean
  image_url: string | null
}

export interface ProductUpdateRequest {
  name?: string
  description?: string | null
  price?: number
  is_available?: boolean
  image_url?: string | null
}

export interface StoreCreateRequest {
  name: string
  description: string | null
  location: string | null
  is_active: boolean
}

export interface StoreUpdateRequest {
  name?: string
  description?: string | null
  location?: string | null
  is_active?: boolean
}

export async function listStoresRequest(): Promise<Store[]> {
  const { data } = await apiClient.get<Store[]>('/stores')
  return data
}

export async function getStoreRequest(storeId: number): Promise<Store> {
  const { data } = await apiClient.get<Store>(`/stores/${storeId}`)
  return data
}

export async function createStoreRequest(payload: StoreCreateRequest): Promise<Store> {
  const { data } = await apiClient.post<Store>('/stores', payload)
  return data
}

export async function updateStoreRequest(storeId: number, payload: StoreUpdateRequest): Promise<Store> {
  const { data } = await apiClient.put<Store>(`/stores/${storeId}`, payload)
  return data
}

export async function listStoreProductsRequest(storeId: number): Promise<Product[]> {
  const { data } = await apiClient.get<Product[]>(`/stores/${storeId}/products`)
  return data
}

export async function createProductRequest(payload: ProductCreateRequest): Promise<Product> {
  const { data } = await apiClient.post<Product>('/products', payload)
  return data
}

export async function updateProductRequest(productId: number, payload: ProductUpdateRequest): Promise<Product> {
  const { data } = await apiClient.put<Product>(`/products/${productId}`, payload)
  return data
}

export async function deleteProductRequest(productId: number): Promise<void> {
  await apiClient.delete(`/products/${productId}`)
}
