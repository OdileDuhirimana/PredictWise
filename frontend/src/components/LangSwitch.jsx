import React from 'react'
import { useI18n } from '../i18n/LanguageContext.jsx'

export default function LangSwitch(){
  const { lang, setLang } = useI18n()
  return (
    <select value={lang} onChange={e=>setLang(e.target.value)}>
      <option value="en">EN</option>
      <option value="rw">RW</option>
    </select>
  )
}
