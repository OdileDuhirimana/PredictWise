import React from 'react'

const SettingsContext = React.createContext({ dyslexia: false, colorblind: false, set: ()=>{} })

export function useSettings(){ return React.useContext(SettingsContext) }

export function SettingsProvider({children}){
  const [dyslexia, setDyslexia] = React.useState(()=> localStorage.getItem('a11y_dys') === '1')
  const [colorblind, setColorblind] = React.useState(()=> localStorage.getItem('a11y_cb') === '1')

  React.useEffect(()=>{
    try{ localStorage.setItem('a11y_dys', dyslexia? '1':'0') }catch{}
    try{ localStorage.setItem('a11y_cb', colorblind? '1':'0') }catch{}
    const root = document.documentElement
    root.classList.toggle('cb', !!colorblind)
    root.classList.toggle('dyslexia', !!dyslexia)
  },[dyslexia, colorblind])

  const setVal = (k,v)=>{
    if(k==='dyslexia') setDyslexia(!!v)
    if(k==='colorblind') setColorblind(!!v)
  }

  return (
    <SettingsContext.Provider value={{ dyslexia, colorblind, set: setVal }}>
      {children}
    </SettingsContext.Provider>
  )
}
