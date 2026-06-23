import React from 'react'
import api from '../api'

export default function Connectivity(){
  const [ok,setOk]=React.useState(true)
  React.useEffect(()=>{
    let alive=true
    const ping=()=> api.get('/health').then(()=> alive&&setOk(true)).catch(()=> alive&&setOk(false))
    ping()
    const id = setInterval(ping, 5000)
    return ()=>{ alive=false; clearInterval(id) }
  },[])
  return (
    <div style={{display:'inline-flex', alignItems:'center', gap:8}}>
      <span title={ok? 'Connected to backend':'Backend offline'} style={{display:'inline-block', width:10, height:10, borderRadius:999, background: ok? 'var(--accent)':'var(--danger)'}} />
      <span className="muted" style={{fontSize:12}}>{ok? 'Online':'Offline'}</span>
    </div>
  )
}
