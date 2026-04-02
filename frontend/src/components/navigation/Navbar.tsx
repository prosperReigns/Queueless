import { Link } from 'react-router-dom'
import { useAuth } from '../../hooks/useAuth'

export function Navbar() {
  const { user, logout } = useAuth()

  return (
    <header>
      <nav>
        <Link to="/">Queue-less</Link>
        {user ? (
          <button type="button" onClick={logout}>
            Logout
          </button>
        ) : (
          <Link to="/auth/login">Login</Link>
        )}
      </nav>
    </header>
  )
}
