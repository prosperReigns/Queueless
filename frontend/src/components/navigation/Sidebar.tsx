import { Link } from 'react-router-dom'

export function Sidebar() {
  return (
    <aside className="dashboard-sidebar">
      <ul className="dashboard-sidebar__nav">
        <li><Link to="/dashboard/merchant">Dashboard</Link></li>
        <li><Link to="/dashboard/merchant/orders">Orders</Link></li>
        <li><Link to="/dashboard/merchant/products">Products</Link></li>
        <li><Link to="/dashboard/merchant/store">Store</Link></li>
        <li><Link to="/dashboard/kitchen">Kitchen display</Link></li>
        <li><Link to="/dashboard/fulfillment">Collection desk</Link></li>
        <li><Link to="/dashboard/merchant/reports">Branch reports</Link></li>
      </ul>
    </aside>
  )
}
