import { Outlet } from 'react-router-dom'
import { Navbar } from '../components/navigation/Navbar'

export function AppLayout() {
  return (
    <div>
      <Navbar />
      <main>
        <Outlet />
      </main>
    </div>
  )
}
