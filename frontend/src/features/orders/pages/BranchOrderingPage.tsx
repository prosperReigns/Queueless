import { useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { useParams } from 'react-router-dom'
import {
  createBranchOrderRequest, getPublicBranchMenuByIdRequest, getQrBranchMenuRequest,
  initiateBranchPaymentRequest, listPublicBusinessBranchesRequest,
} from '../../../api/qless'

export function BranchOrderingPage() {
  const { token } = useParams<{token?:string}>()
  const [businessSlug,setBusinessSlug]=useState('')
  const [submittedSlug,setSubmittedSlug]=useState('')
  const [branchId,setBranchId]=useState('')
  const [quantities,setQuantities]=useState<Record<string,number>>({})
  const [customerName,setCustomerName]=useState('')
  const [customerEmail,setCustomerEmail]=useState('')
  const [customerPhone,setCustomerPhone]=useState('')
  const [fulfillmentMethod,setFulfillmentMethod]=useState<'self_collection'|'external_rider'>('self_collection')
  const branches=useQuery({queryKey:['public-business-branches',submittedSlug],queryFn:()=>listPublicBusinessBranchesRequest(submittedSlug),enabled:Boolean(submittedSlug)&&!token})
  const menu=useQuery({
    queryKey:token?['public-qr-menu',token]:['public-branch-menu',branchId],
    queryFn:()=>token?getQrBranchMenuRequest(token):getPublicBranchMenuByIdRequest(branchId),
    enabled:Boolean(token||branchId),
  })
  const items=(menu.data?.categories??[]).flatMap(category=>category.items.map(item=>({...item,categoryName:category.name})))
  const selected=items.filter(item=>(quantities[item.id]??0)>0&&item.is_available)
  const total=selected.reduce((sum,item)=>sum+Number(item.price)*(quantities[item.id]??0),0)
  const checkout=useMutation({
    mutationFn:async()=>{
      const order=await createBranchOrderRequest({
        ...(token?{branch_qr_token:token}:{branch_id:branchId}),
        source:token?'onsite_qr':'preorder',
        fulfillment_method:fulfillmentMethod,
        customer_name:customerName.trim(),customer_email:customerEmail.trim(),customer_phone:customerPhone.trim(),
        items:selected.map(item=>({menu_item_id:item.id,quantity:quantities[item.id]})),
      })
      if(order.guest_access_token) sessionStorage.setItem('qless:guest-order:'+order.id,order.guest_access_token)
      const callbackUrl=window.location.origin+'/track/'+order.id
      const payment=await initiateBranchPaymentRequest(order.id,callbackUrl,order.guest_access_token??undefined)
      window.location.assign(payment.authorization_url)
      return order.id
    },
  })
  return <section className="page-container qless-ops-page">
    <header className="page-header"><h1>{token?'Scan & order':'Find a restaurant'}</h1><p>{token?'You are ordering from the branch identified by its permanent QR code.':'Choose a restaurant and branch to place a preorder.'}</p></header>
    {!token&&<section className="store-card qless-handoff-form">
      <form onSubmit={e=>{e.preventDefault();setSubmittedSlug(businessSlug.trim().toLowerCase());setBranchId('');setQuantities({})}}>
        <label>Restaurant business slug<input className="form-input" value={businessSlug} onChange={e=>setBusinessSlug(e.target.value)} placeholder="e.g. the-green-kitchen" required /></label>
        <button type="submit">Find branches</button>
      </form>
      {branches.isError&&<p className="inline-alert">No branches could be loaded. Check the business slug.</p>}
      {branches.data&&<label>Choose branch<select className="form-input" value={branchId} onChange={e=>{setBranchId(e.target.value);setQuantities({})}}><option value="">Select branch</option>{branches.data.map(branch=><option key={branch.id} value={branch.id}>{branch.name}{branch.city?', '+branch.city:''}</option>)}</select></label>}
    </section>}
    {menu.data&&<section className="store-card">
      <h2>{menu.data.business.name} · {menu.data.branch.name}</h2>
      <p className="muted-text">{menu.data.branch.city??''} {menu.data.branch.state??''}</p>
      {menu.data.categories.map(category=><div key={category.id}><h3>{category.name}</h3><div className="qless-ticket-grid">{category.items.map(item=><article className="product-card" key={item.id}>
        <strong>{item.name}</strong><p>{item.description}</p><p>₦{Number(item.price).toLocaleString()}</p>
        {!item.is_available?<span className="muted-text">Currently unavailable</span>:<label>Quantity<input className="form-input" type="number" min="0" max="50" value={quantities[item.id]??0} onChange={e=>setQuantities(current=>({...current,[item.id]:Math.max(0,Math.min(50,Number(e.target.value)||0))}))}/></label>}
      </article>)}</div></div>)}
    </section>}
    {menu.isError&&<p className="inline-alert">Unable to load this branch menu. The QR code or branch may be inactive.</p>}
    {menu.data&&selected.length>0&&<section className="store-card qless-handoff-form">
      <h2>Checkout</h2>
      <label>Your name<input className="form-input" value={customerName} onChange={e=>setCustomerName(e.target.value)} required /></label>
      <label>Email<input className="form-input" type="email" value={customerEmail} onChange={e=>setCustomerEmail(e.target.value)} required /></label>
      <label>Phone<input className="form-input" type="tel" value={customerPhone} onChange={e=>setCustomerPhone(e.target.value)} required /></label>
      <label>Fulfillment<select className="form-input" value={fulfillmentMethod} onChange={e=>setFulfillmentMethod(e.target.value as 'self_collection'|'external_rider')}><option value="self_collection">I'll collect my order</option><option value="external_rider">I'll arrange an external rider</option></select></label>
      <p><strong>Total: ₦{total.toLocaleString()}</strong></p>
      <button disabled={!customerName.trim()||!customerEmail.trim()||!customerPhone.trim()||checkout.isPending} onClick={()=>checkout.mutate()}>{checkout.isPending?'Creating order…':'Place order and pay'}</button>
      {checkout.isError&&<p className="inline-alert">Checkout could not be completed. If you see a payment attempt on your statement, contact the branch before retrying.</p>}
      <p className="muted-text">Prices and availability are revalidated by Qless when the order is created. Payment is confirmed server-side by Paystack.</p>
    </section>}
  </section>
}
