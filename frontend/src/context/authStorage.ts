import type { AuthState } from '../types/auth'

export const TOKEN_KEY = 'queueless_token'

export const clearStoredAuth = () => {
  localStorage.removeItem(TOKEN_KEY)
}

export const storeToken = (token: string) => {
  localStorage.setItem(TOKEN_KEY, token)
}

export const getStoredToken = () => localStorage.getItem(TOKEN_KEY)

export const getInitialAuthState = (): AuthState => {
  const token = getStoredToken()
  return { user: null, token }
}
