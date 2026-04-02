import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import axios from 'axios'
import { listStoresRequest } from '../../../api/stores'

export function StoresPage() {
  const { data, isLoading, isError, error, refetch, isFetching } = useQuery({
    queryKey: ['stores'],
    queryFn: listStoresRequest,
  })

  const errorMessage = axios.isAxiosError<{ detail?: string }>(error)
    ? error.response?.data?.detail ?? 'Unable to load stores right now.'
    : 'Unable to load stores right now.'

  return (
    <section className="page-container">
      <header className="page-header">
        <h1>Browse Stores</h1>
        <p>Choose a store to view available products.</p>
      </header>

      {isLoading ? <p>Loading stores...</p> : null}

      {isError ? (
        <div className="inline-alert">
          <p>{errorMessage}</p>
          <button type="button" onClick={() => void refetch()} disabled={isFetching}>
            {isFetching ? 'Retrying...' : 'Try again'}
          </button>
        </div>
      ) : null}

      {!isLoading && !isError && data?.length === 0 ? (
        <p className="muted-text">No stores are available yet.</p>
      ) : null}

      {!isLoading && !isError && data && data.length > 0 ? (
        <div className="store-grid">
          {data.map((store) => (
            <article key={store.id} className={`store-card ${store.is_active ? '' : 'store-card--inactive'}`}>
              <div>
                <h2>{store.name}</h2>
                {store.location ? <p>{store.location}</p> : <p className="muted-text">Location not specified</p>}
                {store.description ? (
                  <p className="store-card__description">{store.description}</p>
                ) : (
                  <p className="muted-text">No description available.</p>
                )}
              </div>
              <div className="store-card__footer">
                <span
                  className={`status-badge ${store.is_active ? 'status-badge--active' : 'status-badge--muted'}`}
                >
                  {store.is_active ? 'Open' : 'Closed'}
                </span>
                <Link to={`/stores/${store.id}`} className="button-link">
                  View Products
                </Link>
              </div>
            </article>
          ))}
        </div>
      ) : null}
    </section>
  )
}
