import { useState } from 'react'
import type { FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import axios from 'axios'
import { loginRequest, meRequest } from '../../../api/auth'
import { clearStoredAuth, storeToken } from '../../../context/authStorage'
import { useAuth } from '../../../hooks/useAuth'
import { DASHBOARD_PATH_BY_ROLE } from '../../../routes/dashboardPaths'

export function LoginPage() {
  const navigate = useNavigate()
  const { login } = useAuth()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const onSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setIsSubmitting(true)
    setError(null)

    try {
      const tokenPair = await loginRequest({ email, password })
      storeToken(tokenPair.access_token)
      const user = await meRequest()
      login(user, tokenPair.access_token)
      navigate(DASHBOARD_PATH_BY_ROLE[user.role], { replace: true })
    } catch (error) {
      clearStoredAuth()
      if (axios.isAxiosError<{ detail?: string }>(error)) {
        setError(error.response?.data?.detail ?? 'Unable to sign in. Please try again.')
      } else {
        setError('Unable to sign in. Please try again.')
      }
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <main>
      <h1>Login</h1>
      <form onSubmit={onSubmit}>
        <label htmlFor="login-email">Email</label>
        <input
          id="login-email"
          type="email"
          required
          value={email}
          onChange={(event) => setEmail(event.target.value)}
        />

        <label htmlFor="login-password">Password</label>
        <input
          id="login-password"
          type="password"
          required
          minLength={8}
          value={password}
          onChange={(event) => setPassword(event.target.value)}
        />

        {error ? <p>{error}</p> : null}
        <button type="submit" disabled={isSubmitting}>
          {isSubmitting ? 'Signing in...' : 'Sign in'}
        </button>
      </form>
    </main>
  )
}
