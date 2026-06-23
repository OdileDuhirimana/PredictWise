import React from 'react'
import { Navigate, useLocation } from 'react-router-dom'
import { useAuth } from './AuthContext.jsx'

export default function ProtectedRoute({ children }){
  const { token } = useAuth()
  const loc = useLocation()
  if (!token) {
    const to = `/login?next=${encodeURIComponent(loc.pathname + loc.search)}`
    return <Navigate to={to} replace />
  }
  return children
}
