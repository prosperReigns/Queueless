import { Navigate, Outlet } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'
import { DASHBOARD_PATH_BY_ROLE } from './dashboardPaths'
import { Loader } from '../components/common/Loader'

export function PublicOnlyRoute() {
  const { user, isInitializing } = useAuth()

  if (isInitializing) {
    return <Loader />
  }

  if (user) {
    return <Navigate to={DASHBOARD_PATH_BY_ROLE[user.role] ?? '/unauthorized'} replace />
  }

  return <Outlet />
}
