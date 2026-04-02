import { Link } from 'react-router-dom'
import { useAuth } from '../../hooks/useAuth'
import { useCart } from '../../hooks/useCart'

export function Navbar() {
  const { user, logout } = useAuth()
  const { itemCount } = useCart()

  return (
    <header>
      <nav>
        <Link to="/">Queue-less</Link>
        {user ? (
          <>
            {user.role === 'CUSTOMER' ? (
              <Link to="/cart">Cart ({itemCount})</Link>
            ) : null}
            <button type="button" onClick={logout}>
              Logout
            </button>
          </>
        ) : (
          <Link to="/auth/login">Login</Link>
        )}
      </nav>
    </header>
  )
}
