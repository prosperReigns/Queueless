import type { AuthState } from '../types/auth'

export const ACCESS_TOKEN_KEY = 'queueless_access_token'
export const REFRESH_TOKEN_KEY = 'queueless_refresh_token'
export const TOKEN_KEY = ACCESS_TOKEN_KEY
const LEGACY_TOKEN_KEY = 'queueless_token'

let inMemoryAccessToken: string | null = null
let inMemoryRefreshToken: string | null = null

export const clearStoredAuth = () => {
  inMemoryAccessToken = null
  inMemoryRefreshToken = null
  localStorage.removeItem(ACCESS_TOKEN_KEY)
  localStorage.removeItem(REFRESH_TOKEN_KEY)
  localStorage.removeItem(LEGACY_TOKEN_KEY)
}

export const storeTokens = (accessToken: string, refreshToken?: string) => {
  inMemoryAccessToken = accessToken
  localStorage.setItem(ACCESS_TOKEN_KEY, accessToken)

  if (refreshToken) {
    inMemoryRefreshToken = refreshToken
    localStorage.setItem(REFRESH_TOKEN_KEY, refreshToken)
  }
}

export const storeToken = (token: string) => {
  storeTokens(token)
}

export const getStoredAccessToken = () => {
  const persistedAccessToken =
    localStorage.getItem(ACCESS_TOKEN_KEY) ?? localStorage.getItem(LEGACY_TOKEN_KEY)

  if (inMemoryAccessToken !== persistedAccessToken) {
    inMemoryAccessToken = persistedAccessToken
  }

  return inMemoryAccessToken
}

export const getStoredRefreshToken = () => {
  const persistedRefreshToken = localStorage.getItem(REFRESH_TOKEN_KEY)

  if (inMemoryRefreshToken !== persistedRefreshToken) {
    inMemoryRefreshToken = persistedRefreshToken
  }

  return inMemoryRefreshToken
}

export const getStoredToken = () => {
  return getStoredAccessToken()
}

export const getInitialAuthState = (): AuthState => {
  const token = getStoredAccessToken()
  return { user: null, token }
}
