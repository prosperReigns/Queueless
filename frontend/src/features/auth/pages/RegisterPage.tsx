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
    <main>
      <h1>Register</h1>
      <form onSubmit={onSubmit}>
        <label htmlFor="register-email">Email</label>
        <input
          id="register-email"
          type="email"
          required
          value={email}
          onChange={(event) => setEmail(event.target.value)}
        />

        <label htmlFor="register-password">Password</label>
        <input
          id="register-password"
          type="password"
          required
          minLength={8}
          value={password}
          onChange={(event) => setPassword(event.target.value)}
        />

        <label htmlFor="register-role">Role</label>
        <select
          id="register-role"
          value={role}
          onChange={(event) => setRole(event.target.value as Extract<UserRole, 'CUSTOMER' | 'MERCHANT'>)}
        >
          <option value="CUSTOMER">Customer</option>
          <option value="MERCHANT">Merchant</option>
        </select>

        {error ? <p>{error}</p> : null}
        <button type="submit" disabled={isSubmitting}>
          {isSubmitting ? 'Creating account...' : 'Create account'}
        </button>
      </form>
    </main>
  )
}
