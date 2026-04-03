import { Link } from 'react-router-dom'
import { useAuth } from '../../hooks/useAuth'
import { useCart } from '../../hooks/useCart'

export function Navbar() {
  const { user, logout } = useAuth()
  const { itemCount } = useCart()

  return (
    <header className="app-navbar">
      <nav className="app-navbar__inner">
        <Link to="/" className="app-navbar__brand">
          Queue-less
        </Link>
        <div className="app-navbar__actions">
          {user ? (
            <>
              {user.role === 'CUSTOMER' ? (
                <Link to="/cart" className="button-link">
                  Cart ({itemCount})
                </Link>
              ) : null}
              <button type="button" onClick={logout}>
                Logout
              </button>
            </>
          ) : (
            <Link to="/auth/login" className="button-link">
              Login
            </Link>
          )}
        </div>
      </nav>
    </header>
  )
}
