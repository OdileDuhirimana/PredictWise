import React from 'react'
import { Outlet, useNavigate, Link } from 'react-router-dom'
import { setToken } from '../api'
import Sidebar from '../components/Sidebar.jsx'
import Connectivity from '../components/Connectivity.jsx'
import { useAuth } from '../auth/AuthContext.jsx'
import LangSwitch from '../components/LangSwitch.jsx'
import { useSettings } from '../a11y/SettingsContext.jsx'

export default function App(){
  const navigate = useNavigate()
  const { token, setToken: setAuthToken } = useAuth()
  const { dyslexia, colorblind, set: setA11y } = useSettings()
  const logout = () => { localStorage.removeItem('jwt'); setToken(null); navigate('/login') }
  React.useEffect(()=>{
    const t = localStorage.getItem('jwt'); if(t) setToken(t)
  },[])
  return (
    <div className="container layout">
      <Sidebar />
      <main className="content">
        <div style={{display:'flex', alignItems:'center', justifyContent:'space-between', marginBottom:12}}>
          <h1>Welcome</h1>
          <div className="row" style={{gap:12}}>
            <Connectivity />
            <LangSwitch />
            <label className="row" style={{gap:6}} title="Dyslexia-friendly font"><input type="checkbox" checked={dyslexia} onChange={e=>setA11y('dyslexia', e.target.checked)} /> Dyslexia</label>
            <label className="row" style={{gap:6}} title="Colorblind-friendly palette"><input type="checkbox" checked={colorblind} onChange={e=>setA11y('colorblind', e.target.checked)} /> CB</label>
            {token ? (
              <button onClick={logout} className="button button-ghost button-sm">Logout</button>
            ) : (
              <Link to="/login" className="button button-primary button-sm">Login</Link>
            )}
          </div>
        </div>
        <Outlet />
      </main>
    </div>
  )
}
