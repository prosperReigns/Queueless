import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import axios from 'axios'
import {
  listAdminStoresRequest,
  listAdminUsersRequest,
  setAdminStoreActiveRequest,
  setAdminUserActiveRequest,
} from '../../../api/admin'
import { useAuth } from '../../../hooks/useAuth'

export function AdminDashboardPage() {
  const queryClient = useQueryClient()
  const { user: currentUser } = useAuth()

  const usersQuery = useQuery({
    queryKey: ['admin', 'users'],
    queryFn: listAdminUsersRequest,
  })

  const storesQuery = useQuery({
    queryKey: ['admin', 'stores'],
    queryFn: listAdminStoresRequest,
  })

  const setUserActiveMutation = useMutation({
    mutationFn: ({ userId, isActive }: { userId: string; isActive: boolean }) =>
      setAdminUserActiveRequest(userId, isActive),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['admin', 'users'] })
    },
  })

  const setStoreActiveMutation = useMutation({
    mutationFn: ({ storeId, isActive }: { storeId: number; isActive: boolean }) =>
      setAdminStoreActiveRequest(storeId, isActive),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['admin', 'stores'] })
      void queryClient.invalidateQueries({ queryKey: ['stores'] })
    },
  })

  const usersErrorMessage = axios.isAxiosError<{ detail?: string }>(usersQuery.error)
    ? usersQuery.error.response?.data?.detail ?? 'Failed to load users.'
    : 'Failed to load users.'

  const storesErrorMessage = axios.isAxiosError<{ detail?: string }>(storesQuery.error)
    ? storesQuery.error.response?.data?.detail ?? 'Failed to load stores.'
    : 'Failed to load stores.'

  return (
    <section className="page-container admin-dashboard-page">
      <header className="page-header">
        <h1>Admin Dashboard</h1>
        <p>Manage platform users and stores.</p>
      </header>

      <section className="store-card">
        <h2>Users</h2>
        {usersQuery.isLoading ? <p>Loading users...</p> : null}
        {usersQuery.isError ? (
          <div className="inline-alert">
            <p>{usersErrorMessage}</p>
            <button type="button" onClick={() => void usersQuery.refetch()} disabled={usersQuery.isFetching}>
              {usersQuery.isFetching ? 'Retrying...' : 'Try again'}
            </button>
          </div>
        ) : null}
        {!usersQuery.isLoading && !usersQuery.isError && (usersQuery.data?.length ?? 0) === 0 ? (
          <p className="muted-text">No users found.</p>
        ) : null}

        {!usersQuery.isLoading && !usersQuery.isError && (usersQuery.data?.length ?? 0) > 0 ? (
          <div className="admin-list">
            {usersQuery.data?.map((managedUser) => {
              const canDeactivateSelf = currentUser?.id === managedUser.id
              const nextActive = !managedUser.is_active
              return (
                <article key={managedUser.id} className={`store-card ${managedUser.is_active ? '' : 'store-card--inactive'}`}>
                  <div className="store-card__footer">
                    <h3>{managedUser.email}</h3>
                    <span className={`status-badge ${managedUser.is_active ? 'status-badge--active' : 'status-badge--muted'}`}>
                      {managedUser.is_active ? 'Active' : 'Inactive'}
                    </span>
                  </div>
                  <p className="muted-text">Role: {managedUser.role}</p>
                  <button
                    type="button"
                    onClick={() =>
                      setUserActiveMutation.mutate({ userId: managedUser.id, isActive: nextActive })
                    }
                    disabled={setUserActiveMutation.isPending || (canDeactivateSelf && !nextActive)}
                  >
                    {nextActive ? 'Activate' : 'Deactivate'}
                  </button>
                </article>
              )
            })}
          </div>
        ) : null}
      </section>

      <section className="store-card">
        <h2>Stores</h2>
        {storesQuery.isLoading ? <p>Loading stores...</p> : null}
        {storesQuery.isError ? (
          <div className="inline-alert">
            <p>{storesErrorMessage}</p>
            <button type="button" onClick={() => void storesQuery.refetch()} disabled={storesQuery.isFetching}>
              {storesQuery.isFetching ? 'Retrying...' : 'Try again'}
            </button>
          </div>
        ) : null}
        {!storesQuery.isLoading && !storesQuery.isError && (storesQuery.data?.length ?? 0) === 0 ? (
          <p className="muted-text">No stores found.</p>
        ) : null}

        {!storesQuery.isLoading && !storesQuery.isError && (storesQuery.data?.length ?? 0) > 0 ? (
          <div className="admin-list">
            {storesQuery.data?.map((store) => {
              const nextActive = !store.is_active
              return (
                <article key={store.id} className={`store-card ${store.is_active ? '' : 'store-card--inactive'}`}>
                  <div className="store-card__footer">
                    <h3>{store.name}</h3>
                    <span className={`status-badge ${store.is_active ? 'status-badge--active' : 'status-badge--muted'}`}>
                      {store.is_active ? 'Active' : 'Inactive'}
                    </span>
                  </div>
                  <p className="muted-text">Owner ID: {store.owner_id}</p>
                  <button
                    type="button"
                    onClick={() =>
                      setStoreActiveMutation.mutate({ storeId: store.id, isActive: nextActive })
                    }
                    disabled={setStoreActiveMutation.isPending}
                  >
                    {nextActive ? 'Activate' : 'Deactivate'}
                  </button>
                </article>
              )
            })}
          </div>
        ) : null}
      </section>
    </section>
  )
}
