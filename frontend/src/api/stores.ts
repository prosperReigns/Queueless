import { apiClient } from './client'

export interface Store {
  id: number
  name: string
  description: string | null
  location: string | null
  is_active: boolean
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

export async function listStoresRequest(): Promise<Store[]> {
  const { data } = await apiClient.get<Store[]>('/stores')
  return data
}

export async function getStoreRequest(storeId: number): Promise<Store> {
  const { data } = await apiClient.get<Store>(`/stores/${storeId}`)
  return data
}

export async function listStoreProductsRequest(storeId: number): Promise<Product[]> {
  const { data } = await apiClient.get<Product[]>(`/stores/${storeId}/products`)
  return data
}
