import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { listBranchOrdersRequest, listBranchesRequest, listBusinessesRequest } from '../../../api/qless'

export function BranchReportsPage() {
  const [businessId,setBusinessId]=useState('')
  const [branchId,setBranchId]=useState('')
  const businesses=useQuery({queryKey:['qless-businesses'],queryFn:listBusinessesRequest})
  const branches=useQuery({queryKey:['qless-branches',businessId],queryFn:()=>listBranchesRequest(businessId),enabled:Boolean(businessId)})
  const orders=useQuery({queryKey:['qless-branch-orders',branchId],queryFn:()=>listBranchOrdersRequest(branchId),enabled:Boolean(branchId),refetchInterval:30000})
  const rows=orders.data??[]
  const total=rows.reduce((sum,o)=>sum+Number(o.total_amount),0)
  const active=rows.filter(o=>!['completed','cancelled'].includes(o.status.toLowerCase()))
  const cancelled=rows.filter(o=>o.status.toLowerCase()==='cancelled').length
  const paidOrFurther=rows.filter(o=>!['pending','cancelled'].includes(o.status.toLowerCase())).length
  return <section className="page-container qless-ops-page">
    <header className="page-header"><h1>Branch reports</h1><p>Operational snapshot from branch order records. Amounts are shown in the configured order currency.</p></header>
    <div className="qless-filter-row">
      <label>Business<select className="form-input" value={businessId} onChange={e=>{setBusinessId(e.target.value);setBranchId('')}}><option value="">Select business</option>{(businesses.data??[]).map(b=><option key={b.id} value={b.id}>{b.name}</option>)}</select></label>
      <label>Branch<select className="form-input" value={branchId} onChange={e=>setBranchId(e.target.value)} disabled={!businessId}><option value="">Select branch</option>{(branches.data??[]).map(b=><option key={b.id} value={b.id}>{b.name}</option>)}</select></label>
    </div>
    {orders.isLoading&&<p>Loading branch report…</p>}
    {orders.isError&&<p className="inline-alert">Unable to load this branch's orders. Check your membership and try again.</p>}
    {branchId&&!orders.isLoading&&!orders.isError&&<>
      <div className="qless-metric-grid">
        <article className="store-card"><span>Orders</span><strong>{rows.length}</strong></article>
        <article className="store-card"><span>Total value of orders</span><strong>₦{total.toLocaleString()}</strong></article>
        <article className="store-card"><span>Active orders</span><strong>{active.length}</strong></article>
        <article className="store-card"><span>Paid / beyond payment</span><strong>{paidOrFurther}</strong></article>
        <article className="store-card"><span>Cancelled</span><strong>{cancelled}</strong></article>
      </div>
      <section className="store-card"><h2>Recent orders</h2><div className="qless-report-table"><div className="qless-report-row qless-report-row--head"><span>Order</span><span>Status</span><span>Fulfillment</span><span>Amount</span></div>{rows.slice(0,30).map(o=><div className="qless-report-row" key={o.id}><span>#{o.id}</span><span>{o.status}</span><span>{o.fulfillment_method??'—'}</span><span>₦{Number(o.total_amount).toLocaleString()}</span></div>)}</div></section>
    </>}
    <p className="muted-text">This first reporting view is operational, not an accounting statement. Refunds, fees, tax and net settlement are intentionally excluded until a dedicated financial reporting endpoint is available.</p>
  </section>
}
