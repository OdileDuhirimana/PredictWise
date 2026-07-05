import React from 'react'
import api from '../api'
import Card from '../components/Card.jsx'
import Button from '../components/Button.jsx'
import { useNavigate, useSearchParams, Link } from 'react-router-dom'
import { useToast } from '../components/Toast.jsx'
import { getSafeRedirect } from '../utils/getSafeRedirect.js'

export default function Register(){
  const [email,setEmail]=React.useState('')
  const [password,setPassword]=React.useState('')
  const [confirm,setConfirm]=React.useState('')
  const [busy,setBusy]=React.useState(false)
  const [msg,setMsg]=React.useState('')
  const navigate = useNavigate()
  const [params] = useSearchParams()
  // Was previously used unvalidated — an open-redirect vector inconsistent
  // with Login.jsx's already-correct getSafeRedirect() check on the same
  // `next` query param. See utils/getSafeRedirect.js for the shared fix.
  const rawNext = params.get('next') || '/login'
  const next = getSafeRedirect(rawNext)
  const { notify } = useToast()

  const submit = async (e)=>{
    e.preventDefault()
    if(!email || !password){ setMsg('Email and password required'); return }
    if(password !== confirm){ setMsg('Passwords do not match'); return }
    try{
      setBusy(true)
      await api.post('/auth/register',{email,password})
      notify('Registered successfully. Please login.','success')
      navigate(next, { replace: true })
    }catch(err){
      const errMsg = err?.response?.data?.error?.message || 'Registration failed'
      setMsg(errMsg)
      notify(errMsg,'error')
    }finally{
      setBusy(false)
    }
  }

  return (
    <Card title="Register" subtitle="Create an account to access PredictWise">
      <form onSubmit={submit} className="grid-form">
        <label>Email<input value={email} onChange={e=>setEmail(e.target.value)} placeholder="email" /></label>
        <label>Password<input value={password} type="password" onChange={e=>setPassword(e.target.value)} placeholder="password" /></label>
        <label>Confirm Password<input value={confirm} type="password" onChange={e=>setConfirm(e.target.value)} placeholder="confirm password" /></label>
        <div className="row">
          <Button type="submit" disabled={busy}>{busy? 'Creating…':'Create Account'}</Button>
          {msg && <span className="muted">{msg}</span>}
        </div>
        <div className="muted">Already have an account? <Link to="/login">Login</Link></div>
      </form>
    </Card>
  )
}
