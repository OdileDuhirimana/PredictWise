import React from 'react'
import en from './en.json'
import rw from './rw.json'

const maps = { en, rw }
const LanguageContext = React.createContext({ lang: 'en', t: (k)=>k, setLang: ()=>{} })

export function useI18n(){ return React.useContext(LanguageContext) }

export function LanguageProvider({children}){
  const [lang, _setLang] = React.useState(()=> localStorage.getItem('lang') || 'en')
  const setLang = (l)=>{ localStorage.setItem('lang', l); _setLang(l) }
  const dict = maps[lang] || maps.en
  const t = (key)=> {
    const segs = key.split('.')
    let cur = dict
    for(const s of segs){ cur = cur?.[s]; if(cur == null) return key }
    return cur
  }
  return (
    <LanguageContext.Provider value={{ lang, setLang, t }}>
      {children}
    </LanguageContext.Provider>
  )
}
