import React from 'react'
import api from '../api'
import Card from '../components/Card.jsx'
import Button from '../components/Button.jsx'

export default function DigitalTwin(){
  const [form,setForm]=React.useState({avg_score:67, attendance_rate:0.8, homework_completion:0.7, behavior_incidents:0})
  const [res,setRes]=React.useState(null)
  const onChange=(k)=>(e)=> setForm({...form,[k]: e.target.type==='number'? Number(e.target.value): e.target.value})
  const submit=async()=>{ const r = await api.post('/digital-twin/project', form); setRes(r.data) }
  return (
    <div className="grid two-col">
      <Card title="Digital Twin" subtitle="Project outcomes under different improvement scenarios">
        <div className="grid-form">
          <label>Avg Score<input type="number" value={form.avg_score} onChange={onChange('avg_score')} /></label>
          <label>Attendance Rate<input type="number" step="0.01" value={form.attendance_rate} onChange={onChange('attendance_rate')} /></label>
          <label>Homework Completion<input type="number" step="0.01" value={form.homework_completion} onChange={onChange('homework_completion')} /></label>
          <label>Behavior Incidents<input type="number" value={form.behavior_incidents} onChange={onChange('behavior_incidents')} /></label>
          <Button onClick={submit}>Run Projection</Button>
        </div>
      </Card>
      {res && (
        <Card title="Projections" subtitle={`Health: ${res.health_status} (${res.health_score})`}>
          <ul className="list">
            {res.projections.map((p,i)=>(<li key={i}><b>{p.scenario}</b><span className="muted"> — score {p.predicted_score.toFixed(1)} / pass {(p.pass_prob*100).toFixed(1)}%</span></li>))}
          </ul>
        </Card>
      )}
    </div>
  )
}
