import React from 'react'

export default function Spinner({size=16, label}){
  const s = typeof size === 'number' ? `${size}px` : size
  return (
    <span className="spinner" role="status" aria-live="polite" aria-label={label || 'Loading'}>
      <svg width={s} height={s} viewBox="0 0 24 24" className="spinner-svg" aria-hidden>
        <circle className="spinner-track" cx="12" cy="12" r="10" strokeWidth="3" fill="none" />
        <circle className="spinner-indicator" cx="12" cy="12" r="10" strokeWidth="3" strokeLinecap="round" fill="none" />
      </svg>
      {label && <span className="sr-only">{label}</span>}
    </span>
  )
}
