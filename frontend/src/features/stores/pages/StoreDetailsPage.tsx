import { useQuery } from '@tanstack/react-query'
import axios from 'axios'
import { Link, useParams } from 'react-router-dom'
import { ProductCard } from '../../../components/cards/ProductCard'
import { getStoreRequest, listStoreProductsRequest } from '../../../api/stores'

const POSITIVE_INTEGER_PATTERN = /^[1-9]\d*$/

export function StoreDetailsPage() {
  const { storeId } = useParams<{ storeId: string }>()
  const isValidStoreId = typeof storeId === 'string' && POSITIVE_INTEGER_PATTERN.test(storeId)
  const parsedStoreId: number | null = isValidStoreId ? Number(storeId) : null

  const {
    data: store,
    isLoading: isStoreLoading,
    isError: isStoreError,
    error: storeError,
    refetch: refetchStore,
    isFetching: isStoreFetching,
  } = useQuery({
    queryKey: ['store', parsedStoreId],
    queryFn: () => getStoreRequest(parsedStoreId as number),
    enabled: isValidStoreId,
  })

  const {
    data: products,
    isLoading: isProductsLoading,
    isError: isProductsError,
    error: productsError,
    refetch: refetchProducts,
    isFetching: isProductsFetching,
  } = useQuery({
    queryKey: ['store-products', parsedStoreId],
    queryFn: () => listStoreProductsRequest(parsedStoreId as number),
    enabled: isValidStoreId,
  })

  if (!isValidStoreId) {
    return (
      <section className="page-container">
        <h1>Invalid Store</h1>
        <p className="muted-text">The store identifier is invalid.</p>
        <Link to="/" className="button-link">
          Back to stores
        </Link>
      </section>
    )
  }

  const storeErrorMessage = axios.isAxiosError<{ detail?: string }>(storeError)
    ? storeError.response?.data?.detail ?? 'Unable to load store information.'
    : 'Unable to load store information.'

  const productsErrorMessage = axios.isAxiosError<{ detail?: string }>(productsError)
    ? productsError.response?.data?.detail ?? 'Unable to load products for this store.'
    : 'Unable to load products for this store.'

  return (
    <section className="page-container">
      <header className="page-header">
        <Link to="/" className="inline-link">
          ← Back to stores
        </Link>
        <h1>{store?.name ?? 'Store'}</h1>
        {store?.location ? <p>{store.location}</p> : null}
        {store?.description ? <p>{store.description}</p> : <p className="muted-text">No store description.</p>}
      </header>

      {isStoreLoading ? <p>Loading store details...</p> : null}

      {isStoreError ? (
        <div className="inline-alert">
          <p>{storeErrorMessage}</p>
          <button type="button" onClick={() => void refetchStore()} disabled={isStoreFetching}>
            {isStoreFetching ? 'Retrying...' : 'Try again'}
          </button>
        </div>
      ) : null}

      {!isStoreError ? (
        <>
          <div className="products-header">
            <h2>Products</h2>
          </div>

          {isProductsLoading ? <p>Loading products...</p> : null}

          {isProductsError ? (
            <div className="inline-alert">
              <p>{productsErrorMessage}</p>
              <button type="button" onClick={() => void refetchProducts()} disabled={isProductsFetching}>
                {isProductsFetching ? 'Retrying...' : 'Try again'}
              </button>
            </div>
          ) : null}

          {!isProductsLoading && !isProductsError && products?.length === 0 ? (
            <p className="muted-text">No products available for this store yet.</p>
          ) : null}

          {!isProductsLoading && !isProductsError && products && products.length > 0 ? (
            <div className="product-grid">
              {products.map((product) => (
                <ProductCard
                  key={product.id}
                  name={product.name}
                  price={product.price}
                  description={product.description}
                  isAvailable={product.is_available}
                />
              ))}
            </div>
          ) : null}
        </>
      ) : null}
    </section>
  )
}
