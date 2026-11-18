import { useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import axios from 'axios'
import { getKitchenQueueRequest, listBranchesRequest, listBusinessesRequest, updateKitchenTicketRequest } from '../../../api/qless'
import type { KitchenTicket } from '../../../api/qless'

const NEXT: Record<KitchenTicket['status'], KitchenTicket['status'] | null> = {
  new: 'accepted', accepted: 'preparing', preparing: 'ready', ready: null,
}
const LABEL: Record<KitchenTicket['status'], string> = {
  new: 'New', accepted: 'Accepted', preparing: 'Preparing', ready: 'Ready',
}
export function KitchenDashboardPage() {
  const [businessId, setBusinessId] = useState('')
  const [branchId, setBranchId] = useState('')
  const client = useQueryClient()
  const businesses = useQuery({ queryKey: ['qless-businesses'], queryFn: listBusinessesRequest })
  const branches = useQuery({ queryKey: ['qless-branches', businessId], queryFn: () => listBranchesRequest(businessId), enabled: Boolean(businessId) })
  const queue = useQuery({ queryKey: ['qless-kitchen', branchId], queryFn: () => getKitchenQueueRequest(branchId), enabled: Boolean(branchId), refetchInterval: 5000 })
  const advance = useMutation({
    mutationFn: ({ id, status }: { id: number; status: KitchenTicket['status'] }) => updateKitchenTicketRequest(id, status),
    onSuccess: () => client.invalidateQueries({ queryKey: ['qless-kitchen', branchId] }),
  })
  const counts = useMemo(() => (queue.data ?? []).reduce((a, t) => { a[t.status] += 1; return a }, { new: 0, accepted: 0, preparing: 0, ready: 0 }), [queue.data])
  const error = axios.isAxiosError<{detail?:string}>(queue.error) ? queue.error.response?.data?.detail : 'Unable to load kitchen queue.'
  return <section className="page-container qless-ops-page">
    <header className="page-header"><h1>Kitchen display</h1><p>Live branch queue. Ticket transitions are validated by the server.</p></header>
    <div className="qless-filter-row">
      <label>Business<select className="form-input" value={businessId} onChange={e => {setBusinessId(e.target.value);setBranchId('')}}><option value="">Select business</option>{(businesses.data ?? []).map(b => <option key={b.id} value={b.id}>{b.name}</option>)}</select></label>
      <label>Branch<select className="form-input" value={branchId} onChange={e => setBranchId(e.target.value)} disabled={!businessId}><option value="">Select branch</option>{(branches.data ?? []).map(b => <option key={b.id} value={b.id}>{b.name}</option>)}</select></label>
    </div>
    {branchId && <div className="qless-metric-grid">{(['NEW','ACCEPTED','PREPARING','READY'] as const).map(s => <article className="store-card" key={s}><span>{LABEL[s]}</span><strong>{counts[s]}</strong></article>)}</div>}
    {queue.isLoading && <p>Loading kitchen tickets…</p>}
    {queue.isError && <div className="inline-alert"><span>{error}</span><button onClick={() => void queue.refetch()}>Retry</button></div>}
    {branchId && !queue.isLoading && !queue.isError && (queue.data?.length ?? 0) === 0 && <p className="muted-text">No paid orders are waiting in this kitchen.</p>}
    <div className="qless-ticket-grid">{(queue.data ?? []).map(ticket => <article className="store-card qless-ticket" key={ticket.ticket_id}>
      <div className="product-card__header"><h2>Order #{ticket.order_id}</h2><span className="status-badge status-badge--muted">{LABEL[ticket.status]}</span></div>
      <p className="muted-text">{ticket.order_source ?? 'Order'} · {ticket.fulfillment_method ?? 'Collection'} · {ticket.customer_name ?? 'Customer'}</p>
      <ul>{ticket.items.map((item,i) => <li key={i}>{item.quantity} × {item.item_name}</li>)}</ul>
      <p className="muted-text">Received: {ticket.created_at ? new Date(ticket.created_at).toLocaleTimeString() : '—'}</p>
      {NEXT[ticket.status] && <button disabled={advance.isPending} onClick={() => advance.mutate({id:ticket.ticket_id,status:NEXT[ticket.status]!})}>{ticket.status === 'NEW' ? 'Accept order' : ticket.status === 'ACCEPTED' ? 'Start preparing' : 'Mark ready'}</button>}
    </article>)}</div>
    {advance.isError && <p className="inline-alert">Could not update ticket. Refresh and try again.</p>}
  </section>
}
