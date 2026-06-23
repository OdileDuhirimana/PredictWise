import React from 'react'
import { Link, useLocation } from 'react-router-dom'
import logo from '../assets/logo.svg'

export default function Sidebar(){
  const loc = useLocation()
  const items = [
    {to:'/', label:'Dashboard', icon:'📊'},
    {to:'/students', label:'Students', icon:'👩‍🎓'},
    {to:'/data-entry', label:'Data Entry', icon:'📝'},
    {to:'/predict', label:'Predict', icon:'🤖'},
    {to:'/wellness', label:'Wellness', icon:'🧠'},
    {to:'/voice', label:'Voice', icon:'🎙️'},
    {to:'/digital-twin', label:'Digital Twin', icon:'🧬'},
    {to:'/alerts', label:'Alerts', icon:'📡'},
    {to:'/leaderboard', label:'Leaderboard', icon:'🏆'},
    {to:'/retraining', label:'Retraining', icon:'🔁'},
  ]
  return (
    <aside className="sidebar">
      <div className="brand"><img src={logo} alt="PredictWise" style={{height:28}} /></div>
      <nav className="menu">
        {items.map(i=> {
          const active = loc.pathname === i.to
          return (
            <Link key={i.to} to={i.to} className={`menu-item ${active? 'active':''}`}>
              <span className="icon" aria-hidden>{i.icon}</span>
              <span>{i.label}</span>
            </Link>
          )
        })}
      </nav>
      <div className="sidebar-footer muted">
        <div>v0.1 • beta</div>
      </div>
    </aside>
  )
}

