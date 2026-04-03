import axios from 'axios'
import {
  clearStoredAuth,
  getStoredAccessToken,
  getStoredRefreshToken,
  storeTokens,
} from '../context/authStorage'

type RetriableAxiosConfig = {
  _retry?: boolean
}

const DEFAULT_API_BASE_URL = 'http://localhost:8000/api/v1'

export const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL ?? DEFAULT_API_BASE_URL,
  timeout: 15000,
})

apiClient.interceptors.request.use((config) => {
  const token = getStoredAccessToken()

  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }

  return config
})

const refreshClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL ?? DEFAULT_API_BASE_URL,
  timeout: 15000,
})

const performRefresh = async (): Promise<string | null> => {
  const refreshToken = getStoredRefreshToken()
  if (!refreshToken) {
    return null
  }

  try {
    const { data } = await refreshClient.post<{ access_token: string; token_type: string }>(
      '/auth/refresh',
      { refresh_token: refreshToken },
    )
    storeTokens(data.access_token, refreshToken)
    return data.access_token
  } catch (refreshError) {
    if (import.meta.env.DEV) {
      console.error('Token refresh failed', refreshError)
    }
    clearStoredAuth()
    return null
  }
}

apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const status = error?.response?.status as number | undefined
    const originalRequest = error?.config as (typeof error.config & RetriableAxiosConfig) | undefined

    if (status === 401 && originalRequest && !originalRequest._retry) {
      originalRequest._retry = true
      const nextAccessToken = await performRefresh()

      if (nextAccessToken) {
        originalRequest.headers.Authorization = `Bearer ${nextAccessToken}`
        return apiClient(originalRequest)
      }
    }

    return Promise.reject(error)
  },
)
