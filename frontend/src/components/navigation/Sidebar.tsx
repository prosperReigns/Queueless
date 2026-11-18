import { Link } from 'react-router-dom'
import { useAuth } from '../../hooks/useAuth'

export function Sidebar() {
  const { user } = useAuth()
  const isLegacyMerchant = user?.role === 'MERCHANT'
  return (
    <aside className="dashboard-sidebar">
      <ul className="dashboard-sidebar__nav">
        {isLegacyMerchant && <li><Link to="/dashboard/merchant">Dashboard</Link></li>}
        {isLegacyMerchant && <li><Link to="/dashboard/merchant/orders">Legacy orders</Link></li>}
        {isLegacyMerchant && <li><Link to="/dashboard/merchant/products">Legacy products</Link></li>}
        {isLegacyMerchant && <li><Link to="/dashboard/merchant/store">Legacy store</Link></li>}
        <li><Link to="/dashboard/business">Business setup</Link></li>
        <li><Link to="/dashboard/kitchen">Kitchen display</Link></li>
        <li><Link to="/dashboard/fulfillment">Collection desk</Link></li>
        <li><Link to="/dashboard/merchant/reports">Branch reports</Link></li>
      </ul>
    </aside>
  )
}
