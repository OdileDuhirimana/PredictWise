import React from 'react'
import api, { setToken } from '../api'
import Card from '../components/Card.jsx'
import Button from '../components/Button.jsx'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext.jsx'
import { useToast } from '../components/Toast.jsx'
import Spinner from '../components/Spinner.jsx'
import logo from '../assets/logo.svg'

export default function Login(){
  const [email,setEmail]=React.useState('')
  const [password,setPassword]=React.useState('')
  const [msg,setMsg]=React.useState('')
  const [busy,setBusy]=React.useState(false)
  const navigate = useNavigate()
  const [params] = useSearchParams()
  const rawNext = params.get('next') || '/'
  const next = rawNext.startsWith('/') && !rawNext.startsWith('//') && !rawNext.includes(':') ? rawNext : '/'
  const { setToken: setAuthToken } = useAuth()
  const { notify } = useToast()

  const submit = async (e)=>{
    e.preventDefault()
    try{
      setBusy(true)
      const r = await api.post('/auth/login',{email,password})
      const token = r.data.access_token
      localStorage.setItem('jwt', token)
      setToken(token)
      setAuthToken(token)
      setMsg('Logged in! Redirecting...')
      notify('Logged in','success')
      navigate(next, { replace: true })
    }catch(err){
      setMsg('Login failed')
      notify('Login failed','error')
    }finally{
      setBusy(false)
    }
  }

  return (
    <Card title="Login" subtitle="Authenticate to access protected features">
      <div className="row" style={{justifyContent:'center'}}>
        <img src={logo} alt="PredictWise" style={{height:36}} />
      </div>
      <form onSubmit={submit} className="grid-form">
        <label>Email<input value={email} onChange={e=>setEmail(e.target.value)} placeholder="email" /></label>
        <label>Password<input value={password} type="password" onChange={e=>setPassword(e.target.value)} placeholder="password" /></label>
        <div className="row">
          <Button type="submit" disabled={busy}>{busy? (<><Spinner size={14} />&nbsp;Logging in…</>):'Login'}</Button>
          {msg && <span className="muted">{msg}</span>}
        </div>
      </form>
    </Card>
  )
}
