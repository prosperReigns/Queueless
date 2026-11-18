import { useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { useParams } from 'react-router-dom'
import { getFulfillmentTrackingRequest, issueCollectionCredentialRequest } from '../../../api/qless'

export function BranchOrderTrackingPage() {
  const {orderId:raw}=useParams<{orderId:string}>()
  const orderId=raw&&/^[1-9]\d*$/.test(raw)?Number(raw):0
  const [guestToken,setGuestToken]=useState('')
  const [submittedToken,setSubmittedToken]=useState('')
  const tracking=useQuery({queryKey:['branch-order-tracking',orderId,submittedToken],queryFn:()=>getFulfillmentTrackingRequest(orderId,submittedToken||undefined),enabled:Boolean(orderId),refetchInterval:10000})
  const credential=useMutation({mutationFn:()=>issueCollectionCredentialRequest(orderId,submittedToken||undefined)})
  const data=tracking.data
  return <section className="page-container qless-ops-page">
    <header className="page-header"><h1>Order tracking</h1><p>Follow kitchen preparation and collection status for order #{orderId||'—'}.</p></header>
    {orderId===0&&<p className="inline-alert">Invalid order number.</p>}
    <form className="store-card qless-handoff-form" onSubmit={e=>{e.preventDefault();setSubmittedToken(guestToken.trim())}}>
      <label>Guest checkout access token (if you checked out as a guest)<input className="form-input" value={guestToken} onChange={e=>setGuestToken(e.target.value)} autoComplete="off"/></label>
      <button type="submit">Load tracking</button>
    </form>
    {tracking.isLoading&&<p>Loading tracking…</p>}
    {tracking.isError&&<p className="inline-alert">Unable to load tracking. Confirm the order number and guest access token.</p>}
    {data&&<article className="store-card qless-tracking-card">
      <h2>Order #{data.order_id}</h2>
      <dl><dt>Payment / order status</dt><dd>{data.order_status}</dd><dt>Kitchen</dt><dd>{data.kitchen_status??'Awaiting payment confirmation'}</dd><dt>Fulfillment</dt><dd>{data.fulfillment_status??'Not yet available'}</dd><dt>Method</dt><dd>{data.fulfillment_method??'—'}</dd><dt>Scheduled</dt><dd>{data.scheduled_for?new Date(data.scheduled_for).toLocaleString():'As soon as possible'}</dd></dl>
      <button disabled={credential.isPending||data.kitchen_status!=='READY'||data.fulfillment_status==='collected'||data.fulfillment_status==='rider_collected'} onClick={()=>credential.mutate()}>{credential.isPending?'Generating…':'Get collection QR and PIN'}</button>
      {credential.isError&&<p className="inline-alert">Collection credential is unavailable yet. It is issued only after the order is ready.</p>}
      {credential.data&&<div className="qless-credential"><h3>Show this once to collection staff</h3><strong className="qless-pin">{credential.data.pin}</strong><p>Expires: {new Date(credential.data.expires_at).toLocaleString()}</p><textarea className="form-input" readOnly value={credential.data.qr_payload}/><p className="muted-text">Keep this credential private. It is single-use and branch-specific.</p></div>}
    </article>}
  </section>
}
