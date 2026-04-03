import { useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import axios from 'axios'
import {
  createProductRequest,
  deleteProductRequest,
  listStoreProductsRequest,
  listStoresRequest,
  updateProductRequest,
  type Product,
} from '../../../api/stores'
import { useAuth } from '../../../hooks/useAuth'

interface ProductFormState {
  name: string
  description: string
  price: string
  image_url: string
  is_available: boolean
}

const INITIAL_FORM_STATE: ProductFormState = {
  name: '',
  description: '',
  price: '',
  image_url: '',
  is_available: true,
}

function toFormState(product: Product): ProductFormState {
  return {
    name: product.name,
    description: product.description ?? '',
    price: String(product.price),
    image_url: product.image_url ?? '',
    is_available: product.is_available,
  }
}

export function ProductManagementPage() {
  const queryClient = useQueryClient()
  const { user } = useAuth()
  const [selectedStoreId, setSelectedStoreId] = useState<number | null>(null)
  const [editingProductId, setEditingProductId] = useState<number | null>(null)
  const [formState, setFormState] = useState<ProductFormState>(INITIAL_FORM_STATE)
  const [formError, setFormError] = useState<string | null>(null)

  const storesQuery = useQuery({
    queryKey: ['stores'],
    queryFn: listStoresRequest,
  })

  const ownedStores = useMemo(
    () => (storesQuery.data ?? []).filter((store) => store.owner_id === user?.id),
    [storesQuery.data, user?.id],
  )

  const activeStoreId = selectedStoreId ?? ownedStores[0]?.id ?? null

  const productsQuery = useQuery({
    queryKey: ['store-products', activeStoreId],
    queryFn: () => listStoreProductsRequest(activeStoreId as number),
    enabled: activeStoreId !== null,
  })

  const createProductMutation = useMutation({
    mutationFn: createProductRequest,
    onSuccess: async () => {
      if (activeStoreId !== null) {
        await queryClient.invalidateQueries({ queryKey: ['store-products', activeStoreId] })
      }
      setFormState(INITIAL_FORM_STATE)
      setFormError(null)
    },
  })

  const updateProductMutation = useMutation({
    mutationFn: ({ productId, payload }: { productId: number; payload: Parameters<typeof updateProductRequest>[1] }) =>
      updateProductRequest(productId, payload),
    onSuccess: async () => {
      if (activeStoreId !== null) {
        await queryClient.invalidateQueries({ queryKey: ['store-products', activeStoreId] })
      }
      setEditingProductId(null)
      setFormState(INITIAL_FORM_STATE)
      setFormError(null)
    },
  })

  const deleteProductMutation = useMutation({
    mutationFn: deleteProductRequest,
    onSuccess: async () => {
      if (activeStoreId !== null) {
        await queryClient.invalidateQueries({ queryKey: ['store-products', activeStoreId] })
      }
    },
  })

  const availabilityMutation = useMutation({
    mutationFn: ({ productId, isAvailable }: { productId: number; isAvailable: boolean }) =>
      updateProductRequest(productId, { is_available: isAvailable }),
    onSuccess: async () => {
      if (activeStoreId !== null) {
        await queryClient.invalidateQueries({ queryKey: ['store-products', activeStoreId] })
      }
    },
  })

  const isSubmitting = createProductMutation.isPending || updateProductMutation.isPending

  const storesErrorMessage = axios.isAxiosError<{ detail?: string }>(storesQuery.error)
    ? storesQuery.error.response?.data?.detail ?? 'Unable to load stores.'
    : 'Unable to load stores.'

  const productsErrorMessage = axios.isAxiosError<{ detail?: string }>(productsQuery.error)
    ? productsQuery.error.response?.data?.detail ?? 'Unable to load products.'
    : 'Unable to load products.'

  const submitError = createProductMutation.error ?? updateProductMutation.error
  const submitErrorMessage = axios.isAxiosError<{ detail?: string }>(submitError)
    ? submitError.response?.data?.detail ?? 'Unable to save product.'
    : null

  const deleteErrorMessage = axios.isAxiosError<{ detail?: string }>(deleteProductMutation.error)
    ? deleteProductMutation.error.response?.data?.detail ?? 'Unable to delete product.'
    : null

  const availabilityErrorMessage = axios.isAxiosError<{ detail?: string }>(availabilityMutation.error)
    ? availabilityMutation.error.response?.data?.detail ?? 'Unable to update product availability.'
    : null

  const onStoreChange = (value: string) => {
    if (value === '') {
      setSelectedStoreId(null)
      return
    }

    const parsed = Number(value)
    if (Number.isNaN(parsed)) {
      setSelectedStoreId(null)
      return
    }
    setSelectedStoreId(parsed)
    setEditingProductId(null)
    setFormState(INITIAL_FORM_STATE)
    setFormError(null)
    createProductMutation.reset()
    updateProductMutation.reset()
    deleteProductMutation.reset()
    availabilityMutation.reset()
  }

  const onEditClick = (product: Product) => {
    setEditingProductId(product.id)
    setFormState(toFormState(product))
    setFormError(null)
  }

  const onCancelEdit = () => {
    setEditingProductId(null)
    setFormState(INITIAL_FORM_STATE)
    setFormError(null)
  }

  const onFormSubmit = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setFormError(null)

    if (activeStoreId === null) {
      setFormError('Select a store before saving a product.')
      return
    }

    const trimmedName = formState.name.trim()
    const trimmedDescription = formState.description.trim()
    const trimmedImageUrl = formState.image_url.trim()

    if (!trimmedName) {
      setFormError('Product name is required.')
      return
    }

    const trimmedPrice = formState.price.trim()
    if (trimmedPrice === '') {
      setFormError('Price is required.')
      return
    }

    const parsedPrice = Number(trimmedPrice)
    if (!Number.isFinite(parsedPrice) || parsedPrice <= 0) {
      setFormError('Price must be a valid number greater than 0.')
      return
    }

    const payload = {
      name: trimmedName,
      description: trimmedDescription || null,
      price: parsedPrice,
      is_available: formState.is_available,
      image_url: trimmedImageUrl || null,
    }

    if (editingProductId !== null) {
      updateProductMutation.mutate({ productId: editingProductId, payload })
      return
    }

    createProductMutation.mutate({
      store_id: activeStoreId,
      ...payload,
    })
  }

  return (
    <section className="page-container">
      <header className="page-header">
        <h1>Product Management</h1>
        <p>Create, edit, delete, and toggle product availability for your store catalog.</p>
      </header>

      {storesQuery.isLoading ? <p>Loading stores...</p> : null}

      {storesQuery.isError ? (
        <div className="inline-alert">
          <p>{storesErrorMessage}</p>
          <button type="button" onClick={() => void storesQuery.refetch()} disabled={storesQuery.isFetching}>
            {storesQuery.isFetching ? 'Retrying...' : 'Try again'}
          </button>
        </div>
      ) : null}

      {!storesQuery.isLoading && !storesQuery.isError && ownedStores.length === 0 ? (
        <p className="muted-text">You do not own a store yet. Create one first to manage products.</p>
      ) : null}

      {!storesQuery.isLoading && !storesQuery.isError && ownedStores.length > 0 ? (
        <>
          <section className="store-card">
            <label className="form-field">
              <span>Select store</span>
              <select
                value={activeStoreId ?? ''}
                onChange={(event) => onStoreChange(event.target.value)}
                className="form-input"
              >
                {ownedStores.map((store) => (
                  <option key={store.id} value={store.id}>
                    {store.name}
                  </option>
                ))}
              </select>
            </label>
          </section>

          <section className="store-card product-management-form-card">
            <h2>{editingProductId !== null ? 'Edit Product' : 'Create Product'}</h2>
            <form onSubmit={onFormSubmit} className="product-management-form">
              <label className="form-field">
                <span>Name</span>
                <input
                  className="form-input"
                  type="text"
                  value={formState.name}
                  onChange={(event) => setFormState((current) => ({ ...current, name: event.target.value }))}
                  required
                />
              </label>

              <label className="form-field">
                <span>Description</span>
                <textarea
                  className="form-input form-input--textarea"
                  value={formState.description}
                  onChange={(event) => setFormState((current) => ({ ...current, description: event.target.value }))}
                />
              </label>

              <label className="form-field">
                <span>Price (₦)</span>
                <input
                  className="form-input"
                  type="number"
                  min="0"
                  step="0.01"
                  value={formState.price}
                  onChange={(event) => setFormState((current) => ({ ...current, price: event.target.value }))}
                  required
                />
              </label>

              <label className="form-field">
                <span>Image URL</span>
                <input
                  className="form-input"
                  type="url"
                  value={formState.image_url}
                  onChange={(event) => setFormState((current) => ({ ...current, image_url: event.target.value }))}
                />
              </label>

              <label className="form-checkbox">
                <input
                  type="checkbox"
                  checked={formState.is_available}
                  onChange={(event) => setFormState((current) => ({ ...current, is_available: event.target.checked }))}
                />
                <span>Available for purchase</span>
              </label>

              {formError ? (
                <div className="inline-alert">
                  <p>{formError}</p>
                </div>
              ) : null}

              {submitErrorMessage ? (
                <div className="inline-alert">
                  <p>{submitErrorMessage}</p>
                </div>
              ) : null}

              <div className="checkout-summary__actions">
                <button type="submit" disabled={isSubmitting}>
                  {isSubmitting ? 'Saving...' : editingProductId !== null ? 'Save changes' : 'Create product'}
                </button>
                {editingProductId !== null ? (
                  <button type="button" onClick={onCancelEdit} disabled={isSubmitting}>
                    Cancel edit
                  </button>
                ) : null}
              </div>
            </form>
          </section>

          <section>
            <div className="products-header">
              <h2>Products</h2>
              <button type="button" onClick={() => void productsQuery.refetch()} disabled={productsQuery.isFetching}>
                {productsQuery.isFetching ? 'Refreshing...' : 'Refresh products'}
              </button>
            </div>

            {productsQuery.isLoading ? <p>Loading products...</p> : null}

            {productsQuery.isError ? (
              <div className="inline-alert">
                <p>{productsErrorMessage}</p>
              </div>
            ) : null}

            {deleteErrorMessage ? (
              <div className="inline-alert">
                <p>{deleteErrorMessage}</p>
              </div>
            ) : null}

            {availabilityErrorMessage ? (
              <div className="inline-alert">
                <p>{availabilityErrorMessage}</p>
              </div>
            ) : null}

            {!productsQuery.isLoading && !productsQuery.isError && (productsQuery.data?.length ?? 0) === 0 ? (
              <p className="muted-text">No products yet for this store.</p>
            ) : null}

            {!productsQuery.isLoading && !productsQuery.isError && productsQuery.data && productsQuery.data.length > 0 ? (
              <div className="product-grid">
                {productsQuery.data.map((product) => {
                  const isDeleting = deleteProductMutation.isPending && deleteProductMutation.variables === product.id
                  const isUpdatingAvailability = availabilityMutation.isPending && availabilityMutation.variables?.productId === product.id
                  return (
                    <article key={product.id} className="product-card">
                      <div className="product-card__header">
                        <h3>{product.name}</h3>
                        <span className={`status-badge ${product.is_available ? 'status-badge--active' : 'status-badge--muted'}`}>
                          {product.is_available ? 'Available' : 'Unavailable'}
                        </span>
                      </div>
                      {product.description ? (
                        <p className="product-card__description">{product.description}</p>
                      ) : (
                        <p className="muted-text">No description provided.</p>
                      )}
                      <p className="product-card__price">₦{Number(product.price).toLocaleString()}</p>
                      <div className="checkout-summary__actions">
                        <button type="button" onClick={() => onEditClick(product)}>
                          Edit
                        </button>
                        <button
                          type="button"
                          onClick={() => availabilityMutation.mutate({ productId: product.id, isAvailable: !product.is_available })}
                          disabled={isUpdatingAvailability}
                        >
                          {isUpdatingAvailability
                            ? 'Updating...'
                            : product.is_available
                              ? 'Mark unavailable'
                              : 'Mark available'}
                        </button>
                        <button
                          type="button"
                          onClick={() => {
                            deleteProductMutation.mutate(product.id)
                          }}
                          disabled={isDeleting}
                        >
                          {isDeleting ? 'Deleting...' : 'Delete'}
                        </button>
                      </div>
                    </article>
                  )
                })}
              </div>
            ) : null}
          </section>
        </>
      ) : null}
    </section>
  )
}
