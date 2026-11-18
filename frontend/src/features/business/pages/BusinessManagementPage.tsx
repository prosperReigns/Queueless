import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import axios from 'axios'
import {
  createBranchRequest, createBusinessRequest, createMembershipRequest, createMenuCategoryRequest,
  createMenuItemRequest, getPublicBranchMenuRequest, listBranchesRequest, listBusinessesRequest,
  listMembershipsRequest, updateBranchMenuItemRequest, updateMembershipRequest,
} from '../../../api/qless'

export function BusinessManagementPage() {
  const client = useQueryClient()
  const [businessId,setBusinessId] = useState('')
  const [branchId,setBranchId] = useState('')
  const [businessName,setBusinessName] = useState('')
  const [businessType,setBusinessType] = useState<'independent'|'franchise'>('independent')
  const [branchName,setBranchName] = useState('')
  const [city,setCity] = useState('')
  const [staffUserId,setStaffUserId] = useState('')
  const [staffRole,setStaffRole] = useState('kitchen_staff')
  const [categoryName,setCategoryName] = useState('')
  const [itemName,setItemName] = useState('')
  const [itemPrice,setItemPrice] = useState('')
  const [categoryId,setCategoryId] = useState('')
  const businesses = useQuery({queryKey:['qless-businesses'],queryFn:listBusinessesRequest})
  const branches = useQuery({queryKey:['qless-branches',businessId],queryFn:()=>listBranchesRequest(businessId),enabled:Boolean(businessId)})
  const memberships = useQuery({queryKey:['qless-memberships',businessId],queryFn:()=>listMembershipsRequest(businessId),enabled:Boolean(businessId)})
  const menu = useQuery({queryKey:['qless-branch-menu',branchId],queryFn:()=>getPublicBranchMenuRequest(branchId),enabled:Boolean(branchId)})
  const refreshBusiness = () => client.invalidateQueries({queryKey:['qless-businesses']})
  const createBusiness = useMutation({mutationFn:()=>createBusinessRequest({name:businessName.trim(),business_type:businessType}),onSuccess:async b=>{setBusinessId(b.id);setBusinessName('');await refreshBusiness()}})
  const createBranch = useMutation({mutationFn:()=>createBranchRequest(businessId,{name:branchName.trim(),city:city.trim()||undefined,country:'NG'}),onSuccess:async()=>{setBranchName('');setCity('');await client.invalidateQueries({queryKey:['qless-branches',businessId]})}})
  const addStaff = useMutation({mutationFn:()=>createMembershipRequest(businessId,{user_id:staffUserId.trim(),role:staffRole,branch_id:branchId}),onSuccess:async()=>{setStaffUserId('');await client.invalidateQueries({queryKey:['qless-memberships',businessId]})}})
  const toggleStaff = useMutation({mutationFn:({id,active}:{id:string;active:boolean})=>updateMembershipRequest(businessId,id,active),onSuccess:()=>client.invalidateQueries({queryKey:['qless-memberships',businessId]})})
  const addCategory = useMutation({mutationFn:()=>createMenuCategoryRequest(businessId,{name:categoryName.trim()}),onSuccess:async()=>{setCategoryName('');await client.invalidateQueries({queryKey:['qless-branch-menu',branchId]})}})
  const addItem = useMutation({mutationFn:()=>createMenuItemRequest(businessId,{name:itemName.trim(),category_id:categoryId,base_price:Number(itemPrice)}),onSuccess:async()=>{setItemName('');setItemPrice('');await client.invalidateQueries({queryKey:['qless-branch-menu',branchId]})}})
  const toggleItem = useMutation({mutationFn:({id,available}:{id:string;available:boolean})=>updateBranchMenuItemRequest(branchId,id,{is_available:available}),onSuccess:()=>client.invalidateQueries({queryKey:['qless-branch-menu',branchId]})})
  const mutationError = [createBusiness,createBranch,addStaff,addCategory,addItem,toggleStaff,toggleItem].find(m=>m.isError)?.error
  const errorMessage = axios.isAxiosError<{detail?:string}>(mutationError) ? mutationError.response?.data?.detail : mutationError instanceof Error ? mutationError.message : ''
  return <section className="page-container qless-ops-page">
    <header className="page-header"><h1>Business & branch management</h1><p>Set up a restaurant or franchise, assign branch staff and manage the branch menu.</p></header>
    <section className="store-card qless-handoff-form">
      <h2>Create a business</h2>
      <label>Business name<input className="form-input" value={businessName} onChange={e=>setBusinessName(e.target.value)} required /></label>
      <label>Business type<select className="form-input" value={businessType} onChange={e=>setBusinessType(e.target.value as 'independent'|'franchise')}><option value="independent">Independent restaurant</option><option value="franchise">Franchise</option></select></label>
      <button disabled={!businessName.trim()||createBusiness.isPending} onClick={()=>createBusiness.mutate()}>{createBusiness.isPending?'Creating…':'Create business'}</button>
    </section>
    <div className="qless-filter-row">
      <label>Business<select className="form-input" value={businessId} onChange={e=>{setBusinessId(e.target.value);setBranchId('')}}><option value="">Select business</option>{(businesses.data??[]).map(b=><option key={b.id} value={b.id}>{b.name} · {b.membership_role??'staff'}</option>)}</select></label>
      <label>Branch<select className="form-input" value={branchId} onChange={e=>setBranchId(e.target.value)} disabled={!businessId}><option value="">Select branch</option>{(branches.data??[]).map(b=><option key={b.id} value={b.id}>{b.name}</option>)}</select></label>
    </div>
    {businessId&&<div className="qless-management-grid">
      <section className="store-card qless-handoff-form"><h2>Add a branch</h2>
        <label>Branch name<input className="form-input" value={branchName} onChange={e=>setBranchName(e.target.value)} /></label>
        <label>City<input className="form-input" value={city} onChange={e=>setCity(e.target.value)} /></label>
        <button disabled={!branchName.trim()||createBranch.isPending} onClick={()=>createBranch.mutate()}>Add branch</button>
      </section>
      <section className="store-card qless-handoff-form"><h2>Assign branch staff</h2>
        <label>Staff user ID<input className="form-input" value={staffUserId} onChange={e=>setStaffUserId(e.target.value)} placeholder="UUID of an existing Qless user" /></label>
        <label>Role<select className="form-input" value={staffRole} onChange={e=>setStaffRole(e.target.value)}><option value="branch_manager">Branch manager</option><option value="cashier">Cashier</option><option value="kitchen_staff">Kitchen staff</option><option value="collection_staff">Collection staff</option></select></label>
        <button disabled={!branchId||!staffUserId.trim()||addStaff.isPending} onClick={()=>addStaff.mutate()}>Assign to selected branch</button>
        <p className="muted-text">Create the user's account first. Staff assignment is restricted by business-owner permissions on the server.</p>
      </section>
    </div>}
    {memberships.data&&<section className="store-card"><h2>Staff memberships</h2>{memberships.data.map(m=><div className="qless-report-row" key={m.id}><span>{m.user_id.slice(0,8)}…</span><span>{m.role}</span><span>{m.branch_id===null?'All branches':m.branch_id.slice(0,8)+'…'}</span><button disabled={toggleStaff.isPending||m.role==='owner'} onClick={()=>toggleStaff.mutate({id:m.id,active:!m.is_active})}>{m.is_active?'Suspend':'Reactivate'}</button></div>)}</section>}
    {businessId&&<section className="store-card qless-handoff-form"><h2>Menu setup</h2>
      <label>New category<input className="form-input" value={categoryName} onChange={e=>setCategoryName(e.target.value)} /></label>
      <button disabled={!branchId||!categoryName.trim()||addCategory.isPending} onClick={()=>addCategory.mutate()}>Add category</button>
      <label>Item name<input className="form-input" value={itemName} onChange={e=>setItemName(e.target.value)} /></label>
      <label>Category<select className="form-input" value={categoryId} onChange={e=>setCategoryId(e.target.value)}><option value="">Select category</option>{(menu.data??[]).map(c=><option key={c.id} value={c.id}>{c.name}</option>)}</select></label>
      <label>Base price (NGN)<input className="form-input" type="number" min="0.01" step="0.01" value={itemPrice} onChange={e=>setItemPrice(e.target.value)} /></label>
      <button disabled={!itemName.trim()||!categoryId||Number(itemPrice)<=0||addItem.isPending} onClick={()=>addItem.mutate()}>Add menu item</button>
      {!branchId&&<p className="muted-text">Select a branch to view and manage item availability.</p>}
      {menu.data?.map(category=><div key={category.id}><h3>{category.name}</h3>{category.items.map(item=><div className="qless-report-row" key={item.id}><span>{item.name}</span><span>₦{Number(item.price).toLocaleString()}</span><span>{item.is_available?'Available':'Unavailable'}</span><button disabled={!branchId||toggleItem.isPending} onClick={()=>toggleItem.mutate({id:item.id,available:!item.is_available})}>{item.is_available?'Disable':'Enable'}</button></div>)}</div>)}
    </section>}
    {errorMessage&&<div className="inline-alert" role="alert">{errorMessage}</div>}
  </section>
}
