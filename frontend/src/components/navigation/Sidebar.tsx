import { Link } from 'react-router-dom'

export function Sidebar() {
  return (
    <aside className="dashboard-sidebar">
      <ul className="dashboard-sidebar__nav">
        <li>
          <Link to="/dashboard/merchant">Dashboard</Link>
        </li>
        <li>
          <Link to="/dashboard/merchant/orders">Orders</Link>
        </li>
        <li>
          <Link to="/dashboard/merchant/products">Products</Link>
        </li>
      </ul>
    </aside>
  )
}
