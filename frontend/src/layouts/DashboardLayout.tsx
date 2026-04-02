import { Outlet } from 'react-router-dom'
import { Sidebar } from '../components/navigation/Sidebar'

export function DashboardLayout() {
  return (
    <div>
      <Sidebar />
      <main>
        <Outlet />
      </main>
    </div>
  )
}
