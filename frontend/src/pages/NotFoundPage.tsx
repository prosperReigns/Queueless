import { Link } from 'react-router-dom'

export function NotFoundPage() {
  return (
    <section className="page-container">
      <article className="store-card">
        <header className="page-header">
          <h1>Page not found</h1>
          <p className="muted-text">The page you requested does not exist or may have moved.</p>
        </header>
        <div className="checkout-summary__actions">
          <Link to="/" className="button-link">
            Go home
          </Link>
        </div>
      </article>
    </section>
  )
}
