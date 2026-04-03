import { useState } from 'react'
import type { FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import axios from 'axios'
import { registerRequest } from '../../../api/auth'
import type { UserRole } from '../../../types/auth'

export function RegisterPage() {
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [role, setRole] = useState<Extract<UserRole, 'CUSTOMER' | 'MERCHANT'>>('CUSTOMER')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const onSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setIsSubmitting(true)
    setError(null)

    try {
      await registerRequest({ email, password, role })
      navigate('/auth/login', { replace: true })
    } catch (error) {
      if (axios.isAxiosError<{ detail?: string }>(error)) {
        setError(error.response?.data?.detail ?? 'Unable to register account. Please try again.')
      } else {
        setError('Unable to register account. Please try again.')
      }
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <main className="page-container auth-page">
      <section className="auth-card">
        <header className="page-header">
          <h1>Register</h1>
          <p>Create an account to start ordering or managing your store.</p>
        </header>
        <form onSubmit={onSubmit} className="auth-form">
          <label htmlFor="register-email" className="form-field">
            <span>Email</span>
            <input
              id="register-email"
              className="form-input"
              type="email"
              required
              value={email}
              onChange={(event) => setEmail(event.target.value)}
            />
          </label>

          <label htmlFor="register-password" className="form-field">
            <span>Password</span>
            <input
              id="register-password"
              className="form-input"
              type="password"
              required
              minLength={8}
              value={password}
              onChange={(event) => setPassword(event.target.value)}
            />
          </label>

          <label htmlFor="register-role" className="form-field">
            <span>Role</span>
            <select
              id="register-role"
              className="form-input"
              value={role}
              onChange={(event) => setRole(event.target.value as Extract<UserRole, 'CUSTOMER' | 'MERCHANT'>)}
            >
              <option value="CUSTOMER">Customer</option>
              <option value="MERCHANT">Merchant</option>
            </select>
          </label>

          {error ? (
            <div className="inline-alert">
              <p>{error}</p>
            </div>
          ) : null}
          <button type="submit" disabled={isSubmitting}>
            {isSubmitting ? 'Creating account...' : 'Create account'}
          </button>
        </form>
      </section>
    </main>
  )
}
