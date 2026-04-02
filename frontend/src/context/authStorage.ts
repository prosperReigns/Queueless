import type { AuthState } from '../types/auth'

export const TOKEN_KEY = 'queueless_token'
let inMemoryToken: string | null = null

export const clearStoredAuth = () => {
  inMemoryToken = null
  localStorage.removeItem(TOKEN_KEY)
}

export const storeToken = (token: string) => {
  inMemoryToken = token
  localStorage.setItem(TOKEN_KEY, token)
}

export const getStoredToken = () => {
  const persistedToken = localStorage.getItem(TOKEN_KEY)
  if (inMemoryToken !== persistedToken) {
    inMemoryToken = persistedToken
  }
  return inMemoryToken
}

export const getInitialAuthState = (): AuthState => {
  const token = getStoredToken()
  return { user: null, token }
}
