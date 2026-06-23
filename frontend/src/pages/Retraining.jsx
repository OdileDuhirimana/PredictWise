import React from 'react'
import Card from '../components/Card.jsx'
import Button from '../components/Button.jsx'
import api from '../api'
import { useToast } from '../components/Toast.jsx'

export default function Retraining(){
  const { notify } = useToast()
  const [status,setStatus]=React.useState({ trained: false, lastScore: null, lastRun: null })
  const [running,setRunning]=React.useState(false)
  const [scheduled,setScheduled]=React.useState(false)
  const [psi,setPsi]=React.useState(null)

  const check = async ()=>{
    try{
      // Use predict to check if model is trained
      const r = await api.post('/ml/predict', { avg_score: 65, attendance_rate: 0.9, homework_completion: 0.8, behavior_incidents: 0 })
      setStatus(s=> ({ ...s, trained: !!r.data.model_trained }))
    }catch{
      notify('Failed to check model status','error')
    }
  }

  const train = async ()=>{
    try{
      setRunning(true)
      const r = await api.post('/ml/train')
      setStatus({ trained: true, lastScore: r.data.cv_score ?? 0, lastRun: new Date().toISOString() })
      notify('Retraining complete','success')
    }catch{
      notify('Retraining failed','error')
    }finally{ setRunning(false) }
  }

  const fetchPSI = async ()=>{
    try{
      const r = await api.get('/ml/drift')
      setPsi(r.data.psi)
      notify('Drift metrics updated','success')
    }catch{
      notify('Failed to fetch drift metrics','error')
    }
  }

  React.useEffect(()=>{ check() },[])

  React.useEffect(()=>{
    let id
    if (scheduled){
      id = setInterval(train, 60*60*24*1000) // mock daily
    }
    return ()=> id && clearInterval(id)
  },[scheduled])

  return (
    <div className="grid two-col">
      <Card title="Model Status" subtitle="Training status and recent score">
        <div className="grid">
          <div className="row"><h3>Trained</h3><div className="badge">{status.trained? 'Yes':'No'}</div></div>
          <div className="row"><h3>Last CV score</h3><div className="badge">{status.lastScore ?? '—'}</div></div>
          <div className="row"><h3>Last retrain</h3><div className="badge">{status.lastRun ?? '—'}</div></div>
          <div className="row" style={{gap:8}}>
            <Button onClick={train} disabled={running}>{running? 'Retraining…':'Run Retraining'}</Button>
            <Button variant="ghost" onClick={()=> setScheduled(s=>!s)}>{scheduled? 'Disable Daily Schedule':'Enable Daily Schedule'}</Button>
            <Button variant="subtle" onClick={fetchPSI}>Refresh Drift</Button>
          </div>
        </div>
      </Card>
      <Card title="Drift (PSI)" subtitle="Population Stability Index per feature">
        {psi ? (
          <ul className="list">
            {Object.entries(psi).map(([k,v])=> (
              <li key={k}><b>{k}</b><span className="muted"> — {v==null? 'N/A' : v.toFixed ? v.toFixed(4): v}</span></li>
            ))}
          </ul>
        ) : <div className="muted">No drift metrics loaded.</div>}
      </Card>
    </div>
  )
}
