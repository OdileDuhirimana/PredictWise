import React from 'react'

const ToastContext = React.createContext({ notify: () => {} })

export function useToast(){
  return React.useContext(ToastContext)
}

export function ToastProvider({children}){
  const [toasts, setToasts] = React.useState([])
  const notify = (message, variant='info', ttl=3000) => {
    const id = Math.random().toString(36).slice(2)
    setToasts(t => [...t, { id, message, variant }])
    setTimeout(() => setToasts(t => t.filter(x => x.id !== id)), ttl)
  }
  return (
    <ToastContext.Provider value={{ notify }}>
      {children}
      <div className="toasts" role="status" aria-live="polite" aria-atomic="true">
        {toasts.map(t => {
          const role = t.variant === 'error' ? 'alert' : undefined
          return (
            <div key={t.id} className={`toast toast-${t.variant}`} role={role}>{t.message}</div>
          )
        })}
      </div>
    </ToastContext.Provider>
  )
}
