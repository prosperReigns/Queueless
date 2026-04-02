import type { AuthState, AuthUser } from '../types/auth'

export const TOKEN_KEY = 'queueless_token'
export const USER_KEY = 'queueless_user'

export const clearStoredAuth = () => {
  localStorage.removeItem(TOKEN_KEY)
  localStorage.removeItem(USER_KEY)
}

export const storeAuth = (user: AuthUser, token: string) => {
  localStorage.setItem(TOKEN_KEY, token)
  localStorage.setItem(USER_KEY, JSON.stringify(user))
}

export const getStoredToken = () => localStorage.getItem(TOKEN_KEY)

export const getInitialAuthState = (): AuthState => {
  const token = getStoredToken()
  const savedUser = localStorage.getItem(USER_KEY)

  if (!token || !savedUser) {
    return { user: null, token: null }
  }

  try {
    return { user: JSON.parse(savedUser) as AuthUser, token }
  } catch {
    clearStoredAuth()
    return { user: null, token: null }
  }
}
