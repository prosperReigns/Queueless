import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import axios from 'axios'
import { listBranchesRequest, listBusinessesRequest, redeemCollectionRequest } from '../../../api/qless'

export function FulfillmentDashboardPage() {
  const [businessId,setBusinessId] = useState('')
  const [branchId,setBranchId] = useState('')
  const [credential,setCredential] = useState('')
  const [credentialType,setCredentialType] = useState<'pin'|'qr'>('pin')
  const [handoffName,setHandoffName] = useState('')
  const [handoffPhone,setHandoffPhone] = useState('')
  const client=useQueryClient()
  const businesses=useQuery({queryKey:['qless-businesses'],queryFn:listBusinessesRequest})
  const branches=useQuery({queryKey:['qless-branches',businessId],queryFn:()=>listBranchesRequest(businessId),enabled:Boolean(businessId)})
  const redeem=useMutation({mutationFn:()=>redeemCollectionRequest(branchId,{credential_type:credentialType,credential:credential.trim(),handoff_name:handoffName||undefined,handoff_phone:handoffPhone||undefined}),onSuccess:()=>{setCredential('');setHandoffName('');setHandoffPhone('');void client.invalidateQueries({queryKey:['qless-branch-orders',branchId]})}})
  const error=axios.isAxiosError<{detail?:string}>(redeem.error)?redeem.error.response?.data?.detail:'Credential could not be redeemed.'
  return <section className="page-container qless-ops-page">
    <header className="page-header"><h1>Collection & handoff</h1><p>Validate a customer's single-use collection QR or PIN at the correct branch.</p></header>
    <div className="qless-filter-row">
      <label>Business<select className="form-input" value={businessId} onChange={e=>{setBusinessId(e.target.value);setBranchId('')}}><option value="">Select business</option>{(businesses.data??[]).map(b=><option key={b.id} value={b.id}>{b.name}</option>)}</select></label>
      <label>Branch<select className="form-input" value={branchId} onChange={e=>setBranchId(e.target.value)} disabled={!businessId}><option value="">Select branch</option>{(branches.data??[]).map(b=><option key={b.id} value={b.id}>{b.name}</option>)}</select></label>
    </div>
    <form className="store-card qless-handoff-form" onSubmit={e=>{e.preventDefault();redeem.mutate()}}>
      <label>Credential type<select className="form-input" value={credentialType} onChange={e=>setCredentialType(e.target.value as 'pin'|'qr')}><option value="pin">8-digit PIN</option><option value="qr">Collection QR</option></select></label>
      <label>PIN or QR payload<input className="form-input" value={credential} onChange={e=>setCredential(e.target.value)} required autoComplete="off" /></label>
      <label>Rider / recipient name (external rider only)<input className="form-input" value={handoffName} onChange={e=>setHandoffName(e.target.value)} /></label>
      <label>Rider phone (external rider only)<input className="form-input" value={handoffPhone} onChange={e=>setHandoffPhone(e.target.value)} /></label>
      <button type="submit" disabled={!branchId||!credential.trim()||redeem.isPending}>{redeem.isPending?'Validating…':'Validate and complete handoff'}</button>
      <p className="muted-text">The server checks branch, payment, kitchen readiness, expiry and single-use status before completing the handoff.</p>
      {redeem.isError&&<div className="inline-alert" role="alert">{error}</div>}
      {redeem.isSuccess&&<div className="status-badge status-badge--active" role="status">Handoff completed successfully.</div>}
    </form>
  </section>
}
