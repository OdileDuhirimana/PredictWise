import React from 'react'

const AuthContext = React.createContext({ token: null, setToken: ()=>{} })

export function useAuth(){
  return React.useContext(AuthContext)
}

export function AuthProvider({children}){
  const [token, _setToken] = React.useState(()=> localStorage.getItem('jwt'))

  const setToken = (t)=>{
    if (t) localStorage.setItem('jwt', t)
    else localStorage.removeItem('jwt')
    _setToken(t || null)
  }

  React.useEffect(()=>{
    // sync across tabs
    const onStorage = (e)=>{ if(e.key === 'jwt'){ _setToken(e.newValue) } }
    window.addEventListener('storage', onStorage)
    return ()=> window.removeEventListener('storage', onStorage)
  },[])

  return (
    <AuthContext.Provider value={{ token, setToken }}>
      {children}
    </AuthContext.Provider>
  )
}
