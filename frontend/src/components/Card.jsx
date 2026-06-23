import React from 'react'

export default function Card({title, subtitle, actions, children}){
  return (
    <div className="panel" style={{marginBottom:16}}>
      {(title || actions) && (
        <div style={{display:'flex', alignItems:'center', gap:8, marginBottom:10}}>
          <div style={{flex:1}}>
            {title && <div style={{fontWeight:700, fontSize:16}}>{title}</div>}
            {subtitle && <div style={{color:'var(--muted)', fontSize:13}}>{subtitle}</div>}
          </div>
          {actions}
        </div>
      )}
      {children}
    </div>
  )
}
