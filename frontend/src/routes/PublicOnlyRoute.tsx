import { Navigate, Outlet } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'
import { DASHBOARD_PATH_BY_ROLE } from './dashboardPaths'

export function PublicOnlyRoute() {
  const { user } = useAuth()

  if (user) {
    return <Navigate to={DASHBOARD_PATH_BY_ROLE[user.role] ?? '/unauthorized'} replace />
  }

  return <Outlet />
}
