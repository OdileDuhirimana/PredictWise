import React from 'react'
import api from '../api'
import Card from '../components/Card.jsx'
import Button from '../components/Button.jsx'
import { useToast } from '../components/Toast.jsx'

export default function Students(){
  const [items,setItems]=React.useState([])
  const [name,setName]=React.useState('')
  const [grade,setGrade]=React.useState('S3')
  const [className,setClassName]=React.useState('A')
  const [loading,setLoading]=React.useState(true)
  const [saving,setSaving]=React.useState(false)
  const { notify } = useToast()

  const refresh = ()=> api.get('/students/').then(r=>{ setItems(r.data.students); setLoading(false) }).catch(()=>{ setLoading(false); notify('Failed to load students','error') })
  React.useEffect(()=>{refresh()},[])

  const add = async ()=>{
    if(!name.trim()) return
    try{
      setSaving(true)
      await api.post('/students/', {name, grade, class_name: className})
      setName('')
      notify('Student added','success')
      refresh()
    }catch(err){
      notify('Failed to add student','error')
    }finally{
      setSaving(false)
    }
  }

  return (
    <div className="grid two-col">
      <Card title="Add Student" subtitle="Create a new student profile">
        <div className="grid-form">
          <label>Name<input placeholder="Name" value={name} onChange={e=>setName(e.target.value)} /></label>
          <label>Grade<input placeholder="Grade" value={grade} onChange={e=>setGrade(e.target.value)} /></label>
          <label>Class<input placeholder="Class" value={className} onChange={e=>setClassName(e.target.value)} /></label>
          <Button onClick={add} disabled={saving}>{saving? 'Adding…':'Add Student'}</Button>
        </div>
      </Card>
      <Card title="Students" subtitle="All students in the system">
        {loading? <div className="skeleton" style={{height:120}} /> : (
          items.length? (
            <ul className="list">
              {items.map(s=> <li key={s.id}><b>{s.name}</b><span className="muted"> — {s.grade}{s.class_name? (' / '+s.class_name):''}</span></li>)}
            </ul>
          ) : <div className="muted">No students yet.</div>
        )}
      </Card>
    </div>
  )
}
