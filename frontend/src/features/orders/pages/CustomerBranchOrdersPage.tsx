import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { listMyBranchOrdersRequest } from '../../../api/qless'
import { useAuth } from '../../../hooks/useAuth'

export function CustomerBranchOrdersPage() {
  const { user } = useAuth()
  const orders = useQuery({
    queryKey: ['customer-branch-orders', user?.id],
    queryFn: listMyBranchOrdersRequest,
    enabled: Boolean(user?.id),
    refetchInterval: 30000,
  })
  return <section className="page-container">
    <header className="page-header"><h1>Qless order history</h1><p>Remote preorders and orders placed from a branch QR menu.</p></header>
    {orders.isLoading && <p>Loading branch orders…</p>}
    {orders.isError && <p className="inline-alert">Unable to load your branch orders. Please try again.</p>}
    {!orders.isLoading && !orders.isError && orders.data?.length===0 && <p className="muted-text">No Qless branch orders yet. <Link to="/discover" className="inline-link">Find a restaurant</Link>.</p>}
    <div className="merchant-orders-list">{(orders.data??[]).map(order=><article className="store-card" key={order.id}>
      <div className="product-card__header"><h2>Order #{order.id}</h2><span className="status-badge status-badge--muted">{order.status}</span></div>
      <p className="muted-text">{order.order_source==='onsite_qr'?'QR order':'Preorder'} · {order.fulfillment_method??'Collection'}</p>
      <p>Total: ₦{Number(order.total_amount).toLocaleString()}</p>
      <p className="muted-text">{new Date(order.created_at).toLocaleString()}</p>
      <Link to={'/track/'+order.id} className="button-link">Track order</Link>
    </article>)}</div>
  </section>
}
