import { useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import axios from 'axios'
import {
  createStoreRequest,
  listStoresRequest,
  updateStoreRequest,
  type Store,
  type StoreCreateRequest,
} from '../../../api/stores'
import { useAuth } from '../../../hooks/useAuth'

interface StoreFormState {
  name: string
  description: string
  location: string
}

const INITIAL_STORE_FORM: StoreFormState = {
  name: '',
  description: '',
  location: '',
}

function toStoreFormState(store: Store): StoreFormState {
  return {
    name: store.name,
    description: store.description ?? '',
    location: store.location ?? '',
  }
}

export function StoreManagementPage() {
  const queryClient = useQueryClient()
  const { user } = useAuth()
  const [selectedStoreId, setSelectedStoreId] = useState<number | null>(null)
  const [formState, setFormState] = useState<StoreFormState>(INITIAL_STORE_FORM)
  const [formError, setFormError] = useState<string | null>(null)

  const storesQuery = useQuery({
    queryKey: ['stores'],
    queryFn: listStoresRequest,
  })

  const ownedStores = useMemo(
    () => (storesQuery.data ?? []).filter((store) => store.owner_id === user?.id),
    [storesQuery.data, user?.id],
  )

  const activeStore = useMemo(
    () => ownedStores.find((store) => store.id === selectedStoreId) ?? null,
    [ownedStores, selectedStoreId],
  )

  const createStoreMutation = useMutation({
    mutationFn: createStoreRequest,
    onSuccess: async (createdStore) => {
      await queryClient.invalidateQueries({ queryKey: ['stores'] })
      setSelectedStoreId(createdStore.id)
      setFormState(toStoreFormState(createdStore))
      setFormError(null)
    },
  })

  const updateStoreMutation = useMutation({
    mutationFn: ({ storeId, payload }: { storeId: number; payload: Parameters<typeof updateStoreRequest>[1] }) =>
      updateStoreRequest(storeId, payload),
    onSuccess: async (updatedStore) => {
      await queryClient.invalidateQueries({ queryKey: ['stores'] })
      setFormState(toStoreFormState(updatedStore))
      setFormError(null)
    },
  })

  const storesErrorMessage = axios.isAxiosError<{ detail?: string }>(storesQuery.error)
    ? storesQuery.error.response?.data?.detail ?? 'Unable to load stores.'
    : 'Unable to load stores.'

  const submitError = createStoreMutation.error ?? updateStoreMutation.error
  const submitErrorMessage = axios.isAxiosError<{ detail?: string }>(submitError)
    ? submitError.response?.data?.detail ?? 'Unable to save store details.'
    : null

  const isSubmitting = createStoreMutation.isPending || updateStoreMutation.isPending

  const onSelectStore = (storeIdText: string) => {
    const parsed = Number(storeIdText)
    if (Number.isNaN(parsed)) {
      setSelectedStoreId(null)
      setFormState(INITIAL_STORE_FORM)
      return
    }
    const store = ownedStores.find((entry) => entry.id === parsed)
    setSelectedStoreId(parsed)
    setFormState(store ? toStoreFormState(store) : INITIAL_STORE_FORM)
    setFormError(null)
    createStoreMutation.reset()
    updateStoreMutation.reset()
  }

  const onResetCreate = () => {
    setSelectedStoreId(null)
    setFormState(INITIAL_STORE_FORM)
    setFormError(null)
    createStoreMutation.reset()
    updateStoreMutation.reset()
  }

  const validateForm = (): StoreCreateRequest | null => {
    const trimmedName = formState.name.trim()
    const trimmedDescription = formState.description.trim()
    const trimmedLocation = formState.location.trim()

    if (!trimmedName) {
      setFormError('Store name is required.')
      return null
    }
    if (trimmedName.length > 255) {
      setFormError('Store name cannot exceed 255 characters.')
      return null
    }
    if (trimmedDescription.length > 5000) {
      setFormError('Store description cannot exceed 5000 characters.')
      return null
    }
    if (trimmedLocation.length > 255) {
      setFormError('Store location cannot exceed 255 characters.')
      return null
    }

    setFormError(null)
    return {
      name: trimmedName,
      description: trimmedDescription || null,
      location: trimmedLocation || null,
      is_active: true,
    }
  }

  const onSubmit = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    const payload = validateForm()
    if (!payload) {
      return
    }

    if (activeStore) {
      updateStoreMutation.mutate({
        storeId: activeStore.id,
        payload: {
          name: payload.name,
          description: payload.description,
          location: payload.location,
        },
      })
      return
    }

    createStoreMutation.mutate(payload)
  }

  return (
    <section className="page-container">
      <header className="page-header">
        <h1>Store Management</h1>
        <p>Create your store, update details, and review your current store information.</p>
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

      {!storesQuery.isLoading && !storesQuery.isError ? (
        <>
          <section className="store-card">
            <div className="store-card__header">
              <h2>Your stores</h2>
              <button type="button" onClick={onResetCreate}>
                {ownedStores.length > 0 ? 'Create new store' : 'Create your first store'}
              </button>
            </div>

            {ownedStores.length === 0 ? (
              <p className="muted-text">You do not have a store yet.</p>
            ) : (
              <label className="form-field">
                <span>Select store to edit or view</span>
                <select
                  className="form-input"
                  value={activeStore?.id ?? ''}
                  onChange={(event) => onSelectStore(event.target.value)}
                >
                  <option value="">Create new store</option>
                  {ownedStores.map((store) => (
                    <option key={store.id} value={store.id}>
                      {store.name}
                    </option>
                  ))}
                </select>
              </label>
            )}
          </section>

          <section className="store-card product-management-form-card">
            <h2>{activeStore ? 'Edit store details' : 'Create store'}</h2>
            <form onSubmit={onSubmit} className="product-management-form">
              <label className="form-field">
                <span>Store name</span>
                <input
                  className="form-input"
                  type="text"
                  maxLength={255}
                  value={formState.name}
                  onChange={(event) => setFormState((current) => ({ ...current, name: event.target.value }))}
                  required
                />
              </label>

              <label className="form-field">
                <span>Description</span>
                <textarea
                  className="form-input form-input--textarea"
                  maxLength={5000}
                  value={formState.description}
                  onChange={(event) => setFormState((current) => ({ ...current, description: event.target.value }))}
                />
              </label>

              <label className="form-field">
                <span>Location</span>
                <input
                  className="form-input"
                  type="text"
                  maxLength={255}
                  value={formState.location}
                  onChange={(event) => setFormState((current) => ({ ...current, location: event.target.value }))}
                />
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
                  {isSubmitting ? 'Saving...' : activeStore ? 'Save store details' : 'Create store'}
                </button>
              </div>
            </form>
          </section>

          {activeStore ? (
            <section className="store-card">
              <h2>Store information</h2>
              <p>
                <strong>Name:</strong> {activeStore.name}
              </p>
              <p>
                <strong>Location:</strong> {activeStore.location || 'Not specified'}
              </p>
              <p>
                <strong>Description:</strong> {activeStore.description || 'No description provided'}
              </p>
              <p>
                <strong>Status:</strong> {activeStore.is_active ? 'Active' : 'Inactive'}
              </p>
            </section>
          ) : null}
        </>
      ) : null}
    </section>
  )
}
